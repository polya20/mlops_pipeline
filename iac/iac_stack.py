from aws_cdk import (
    Stack, CfnParameter, Duration, RemovalPolicy,
    aws_s3 as s3,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as _lambda,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions
)
from constructs import Construct

class JackpotOptimizerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        image_tag = self.node.try_get_context("image_tag") or "latest"

        # --- 1. Core Infrastructure ---
        # Simple S3 bucket without auto-delete to avoid custom resources
        artifact_bucket = s3.Bucket(self, "ArtifactBucket",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True
        )

        ecr_repository = ecr.Repository.from_repository_name(self, "MLOpsRepo", "jackpot-optimizer")

        # Use existing SageMaker roles for all services (simpler and more reliable)
        sagemaker_execution_role_arn = f"arn:aws:iam::{self.account}:role/AmazonSageMaker-ExecutionRole-20250811T230696"
        
        sagemaker_role = iam.Role.from_role_arn(self, "SageMakerExecutionRole", 
            role_arn=sagemaker_execution_role_arn
        )

        lambda_role = iam.Role.from_role_arn(self, "LambdaExecutionRole",
            role_arn=sagemaker_execution_role_arn
        )

        optimizer_lambda = _lambda.DockerImageFunction(self, "OptimizerFunction",
            code=_lambda.DockerImageCode.from_ecr(ecr_repository, tag_or_digest=image_tag),
            memory_size=1024,
            timeout=Duration.minutes(5),
            environment={"ARTIFACT_BUCKET": artifact_bucket.bucket_name},
            role=lambda_role
        )
        
        # Grant Lambda additional permissions if needed
        optimizer_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["sagemaker:DescribeTrainingJob"],
            resources=["*"]
        ))

        recommendation_topic = sns.Topic(self, "RecommendationTopic")
        recommendation_topic.add_subscription(subscriptions.EmailSubscription("subhojit20@gmail.com")) 

        # --- 2. Step Functions Workflow Definition ---
        
        train_task = sfn_tasks.SageMakerCreateTrainingJob(self, "TrainSalesModel",
            # Remove training_job_name - let CDK auto-generate a compliant one
            role=sagemaker_role,
            algorithm_specification=sfn_tasks.AlgorithmSpecification(
                training_image=sfn_tasks.DockerImage.from_registry(
                    ecr_repository.repository_uri_for_tag(image_tag)
                ),
                training_input_mode=sfn_tasks.InputMode.FILE
            ),
            hyperparameters={
                "config_s3_uri": f"s3://{artifact_bucket.bucket_name}/configs/england.yaml",
                "data_path": f"s3://{artifact_bucket.bucket_name}/data/lottery_sales.csv.gz"
            },
            input_data_config=[
                sfn_tasks.Channel(
                    channel_name="training",
                    data_source=sfn_tasks.DataSource(
                        s3_data_source=sfn_tasks.S3DataSource(
                            s3_data_type=sfn_tasks.S3DataType.S3_PREFIX,
                            s3_location=sfn_tasks.S3Location.from_bucket(artifact_bucket, "data/")
                        )
                    )
                )
            ],
            output_data_config=sfn_tasks.OutputDataConfig(
                s3_output_location=sfn_tasks.S3Location.from_bucket(artifact_bucket, "models/")
            ),
            result_path="$.Model"
        )
        
        optimize_task = sfn_tasks.LambdaInvoke(self, "OptimizeJackpot",
            lambda_function=optimizer_lambda,
            payload=sfn.TaskInput.from_object({
                # Pass the training job ARN - let Lambda handle getting the model artifacts
                "training_job_arn": sfn.JsonPath.string_at("$.Model.TrainingJobArn"),
                "country": "england"
            }),
            result_path="$.Recommendation"
        )
        
        notify_task = sfn_tasks.SnsPublish(self, "NotifyStakeholders",
            topic=recommendation_topic,
            message=sfn.TaskInput.from_json_path_at("$.Recommendation.Payload.body"),
            subject="Weekly Jackpot Recommendation"
        )
        
        failure_state = sfn.Fail(self, "PipelineFailed",
            cause="A step in the MLOps pipeline failed.",
            error="JobFailed"
        )

        chain = sfn.Chain.start(train_task).next(optimize_task).next(notify_task)
        train_task.add_catch(failure_state, result_path="$.error-info")
        optimize_task.add_catch(failure_state, result_path="$.error-info")

        # Use the same SageMaker role for Step Functions
        step_functions_role = iam.Role.from_role_arn(self, "StepFunctionsRole",
            role_arn=sagemaker_execution_role_arn
        )

        state_machine = sfn.StateMachine(self, "JackpotStateMachine",
            definition=chain,
            timeout=Duration.hours(1),
            role=step_functions_role
        )

        # --- 3. Event-Driven Trigger ---
        events.Rule(self, "WeeklyTriggerRule",
            schedule=events.Schedule.cron(minute="0", hour="20", week_day="WED"),
            targets=[targets.SfnStateMachine(state_machine)]
        )
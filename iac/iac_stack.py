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
    aws_sns_subscriptions as subscriptions,
    aws_s3_deployment as s3_deployment
)
from constructs import Construct

class JackpotOptimizerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        image_tag = self.node.try_get_context("image_tag") or "latest"

        artifact_bucket = s3.Bucket(self, "ArtifactBucket", removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True, versioned=True)
        
        # Upload config and data files to S3 for the pipeline to use
        s3_deployment.BucketDeployment(self, "DeployPipelineAssets",
            sources=[s3_deployment.Source.asset("../configs"), s3_deployment.Source.asset("../data")],
            destination_bucket=artifact_bucket, exclude=["*.dvc", "*/.gitignore"]
        )

        ecr_repository = ecr.Repository.from_repository_name(self, "MLOpsRepo", "jackpot-optimizer")

        sagemaker_role = iam.Role(self, "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"),
            ]
        )
        artifact_bucket.grant_read_write(sagemaker_role)

        optimizer_lambda = _lambda.DockerImageFunction(self, "OptimizerFunction",
            code=_lambda.DockerImageCode.from_ecr(ecr_repository, tag=image_tag, cmd=["lambda_handler.optimizer.handler.lambda_handler"]),
            memory_size=1024,
            timeout=Duration.minutes(5),
            environment={"ARTIFACT_BUCKET": artifact_bucket.bucket_name}
        )
        artifact_bucket.grant_read(optimizer_lambda)
        optimizer_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=["arn:aws:secretsmanager:*:*:secret:lottery/*"] # Scope down if needed
        ))

        recommendation_topic = sns.Topic(self, "RecommendationTopic")
        recommendation_topic.add_subscription(subscriptions.EmailSubscription("your-email@example.com")) # <-- CHANGE THIS

        # === Step Functions Workflow ===
        train_task = sfn_tasks.SageMakerCreateTrainingJob(self, "TrainSalesModel",
            training_job_name=sfn.JsonPath.string_at("$$.Execution.Name"),
            role=sagemaker_role,
            algorithm_specification=sfn_tasks.AlgorithmSpecification(
                training_image=sfn_tasks.TrainingImage.from_ecr_repository(ecr_repository, tag=image_tag),
                training_input_mode=sfn_tasks.InputMode.FILE
            ),
            hyper_parameters={
                "config_s3_uri": f"s3://{artifact_bucket.bucket_name}/configs/england.yaml",
                "data_path": f"s3://{artifact_bucket.bucket_name}/data/lottery_sales.csv.gz"
            },
            input_data_config=[sfn_tasks.Channel(channel_name="training", data_source=sfn_tasks.DataSource(
                s3_data_source=sfn_tasks.S3DataSource(
                    s3_data_type=sfn_tasks.S3DataType.S3_PREFIX,
                    s3_uri=f"s3://{artifact_bucket.bucket_name}/data/"
                )
            ))],
            output_data_config=sfn_tasks.OutputDataConfig(s3_output_path=f"s3://{artifact_bucket.bucket_name}/models"),
            result_path="$.Model"
        )

        optimize_task = sfn_tasks.LambdaInvoke(self, "OptimizeJackpot",
            lambda_function=optimizer_lambda,
            payload=sfn.TaskInput.from_object({
                "model_s3_path": sfn.JsonPath.string_at("$.Model.ModelArtifacts.S3ModelArtifacts"),
                "country": "england"
            }),
            result_path="$.Recommendation"
        )
        
        notify_task = sfn_tasks.SnsPublish(self, "NotifyStakeholders",
            topic=recommendation_topic,
            message=sfn.TaskInput.from_json_path_at("$.Recommendation.Payload.body"),
            subject=sfn.JsonPath.string_at("States.Format('Weekly Jackpot Recommendation for {}', $.country)")
        )
        
        failure_state = sfn.Fail(self, "PipelineFailed", cause="A step in the MLOps pipeline failed.")

        chain = sfn.Chain.start(train_task).next(optimize_task).next(notify_task)
        train_task.add_catch(failure_state, result_path="$.error-info")
        optimize_task.add_catch(failure_state, result_path="$.error-info")

        state_machine = sfn.StateMachine(self, "JackpotStateMachine", definition=chain, timeout=Duration.hours(1))

        events.Rule(self, "WeeklyTriggerRule",
            schedule=events.Schedule.cron(minute="0", hour="20", week_day="WED"),
            targets=[targets.SfnStateMachine(state_machine)]
        )
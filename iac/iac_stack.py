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

        artifact_bucket = s3.Bucket(self, "ArtifactBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True
        )
        
        s3_deployment.BucketDeployment(self, "DeployPipelineAssets",
            sources=[
                s3_deployment.Source.asset("../configs"),
                s3_deployment.Source.asset("../data")
            ],
            destination_bucket=artifact_bucket,
            exclude=["*.dvc", "*/.gitignore"]
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
            code=_lambda.DockerImageCode.from_ecr(ecr_repository,
                tag=image_tag,
                cmd=["lambda_handler.optimizer.handler.lambda_handler"]
            ),
            memory_size=1024,
            timeout=Duration.minutes(5),
            environment={"ARTIFACT_BUCKET": artifact_bucket.bucket_name}
        )
        artifact_bucket.grant_read(optimizer_lambda)
        optimizer_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=["arn:aws:secretsmanager:*:*:secret:lottery/*"]
        ))

        recommendation_topic = sns.Topic(self, "RecommendationTopic")
        recommendation_topic.add_subscription(subscriptions.EmailSubscription("your-email@example.com"))

        # --- START OF FIX ---
        # The TrainingImage helper class does not exist. Instead, we construct the ECR image URI manually.
        # The SageMakerCreateTrainingJob task expects the full URI string.
        training_image_uri = ecr_repository.repository_uri_for_tag(image_tag)
        
        train_task = sfn_tasks.SageMakerCreateTrainingJob(self, "TrainSalesModel",
            training_job_name=sfn.JsonPath.string_at("$$.Execution.Name"),
            role=sagemaker_role,
            algorithm_specification=sfn_tasks.AlgorithmSpecification(
                training_image_config=sfn_tasks.TrainingImageConfig(
                    training_image_uri=training_image_uri
                ),
                training_input_mode=sfn_tasks.InputMode.FILE
            ),
            hyper_parameters={
                # Note: The arguments must match what your train.py argparse expects
                "config_s3_uri": f"s3://{artifact_bucket.bucket_name}/configs/england.yaml",
                "data_path": f"s3://{artifact_bucket.bucket_name}/data/lottery_sales.csv.gz"
            },
            # ... (rest of the code is the same) ...
        # --- END OF FIX ---
            input_data_config=[sfn_tasks.Channel(channel_name="training", data_source=sfn_tasks.DataSource(
                s3_data_source=sfn_tasks.S3DataSource(
                    s3_data_type=sfn_tasks.S3DataType.S3_PREFIX,
                    s3_uri=f"s3://{artifact_bucket.bucket_name}/data/"
                )
            ))],
            output_data_config=sfn_tasks.OutputDataConfig(s3_output_path=f"s3://{artifact_bucket.bucket_name}/models"),
            result_path="$.Model"
        )
        
        # ... (rest of the CDK stack is the same) ...
        optimize_task = sfn_tasks.LambdaInvoke(...)
        notify_task = sfn_tasks.SnsPublish(...)
        failure_state = sfn.Fail(...)
        chain = sfn.Chain.start(train_task).next(optimize_task).next(notify_task)
        train_task.add_catch(failure_state, result_path="$.error-info")
        optimize_task.add_catch(failure_state, result_path="$.error-info")
        state_machine = sfn.StateMachine(...)
        rule = events.Rule(...)
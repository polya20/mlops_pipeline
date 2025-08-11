#!/usr/bin/env python3
import aws_cdk as cdk
from iac_stack import JackpotOptimizerStack

# Create the CDK App
app = cdk.App()

# Define the synthesizer with a qualifier to use our custom bootstrap roles
# This is necessary for ECR push permissions in the CI/CD pipeline
qualifier_synthesizer = cdk.DefaultStackSynthesizer(
    qualifier="hnb659fds" # Use the same qualifier from the bootstrap command
)

# Instantiate the MLOps pipeline stack
JackpotOptimizerStack(
    app, 
    "JackpotOptimizerStack",
    synthesizer=qualifier_synthesizer
)

# Synthesize the CloudFormation template
app.synth()
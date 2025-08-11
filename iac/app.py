#!/usr/bin/env python3
import aws_cdk as cdk
from iac_stack import JackpotOptimizerStack

app = cdk.App()
JackpotOptimizerStack(app, "JackpotOptimizerStack")
app.synth()
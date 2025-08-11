# iac/app.py
#!/usr/bin/env python3
import aws_cdk as cdk
from iac_stack import JackpotOptimizerStack

app = cdk.App()

# --- START OF FIX ---
# Define the synthesizer with the qualifier
# This tells the CDK to use the roles and resources from the qualified bootstrap stack
qualifier_synthesizer = cdk.DefaultStackSynthesizer(
    qualifier="hnb659fds"
)

JackpotOptimizerStack(
    app, 
    "JackpotOptimizerStack",
    synthesizer=qualifier_synthesizer # <-- Pass the synthesizer to the stack
)
# --- END OF FIX ---

app.synth()
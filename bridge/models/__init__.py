import json

from peewee import MySQLDatabase, Model
from bridge.playhouse_patch import generate_models

database = MySQLDatabase(
    **json.load(open('config.json'))['database']
)

database.connect()

models = generate_models(database)

User: Model = models['user']
Class: Model = models['class']
Judge: Model = models['judge']
Contest: Model = models['contest']
ContestParticipation: Model = models['contest_participation']
Problem: Model = models['problem']
ContestProblem: Model = models['contest_problem']
Submission: Model = models['submission']
SubmissionTestCase: Model = models['submission_testcase']

# Runtime
Judge: Model = models['judge']
Language: Model = models['language']
RuntimeVersion: Model = models['runtime_version']

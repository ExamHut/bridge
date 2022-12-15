import json

from peewee import MySQLDatabase, Model
from playhouse.reflection import generate_models

database = MySQLDatabase(
    **json.load(open('config.json'))['database']
)

database.connect()

models = generate_models(database)

User: Model = models['user']
Class: Model = models['class']
Judge: Model = models['judge']
Problem: Model = models['problem']
Submission: Model = models['submission']
SubmissionTestCase: Model = models['submission_test_case']

# Runtime
Judge: Model = models['judge']
Language: Model = models['language']
RuntimeVersion: Model = models['runtime_version']

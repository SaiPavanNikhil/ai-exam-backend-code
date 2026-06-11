import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:ikPrYfnbZfXhgaoGYUNDmTetBEIYeUmr@acela.proxy.rlwy.net:18510/railway'

from database import Base, engine
from models.model import User, Candidate, Panel, PanelMember, Interview
from models.question import Question
from models.answer import Answer
from models.SelfAssessmentAnswer import SelfAssessmentAnswer
from models.SelfAssessmentResult import SelfAssessmentResult

Base.metadata.create_all(bind=engine)
print('Tables created!')
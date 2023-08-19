from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

from sqlalchemy import create_engine
engine = create_engine('sqlite:///db.sqlite3?check_same_thread=False', echo=False)


#データベースセッション
Session = sessionmaker(bind=engine)
session = Session()
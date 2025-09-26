from databases import Database
import yaml

with open("configs/config.yaml") as f:
    config = yaml.safe_load(f)

DATABASE_URL = config["database_url"]
database = Database(DATABASE_URL)

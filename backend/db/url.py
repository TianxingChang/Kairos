from os import getenv


def get_db_url() -> str:
    db_driver = getenv("DB_DRIVER", "postgresql+psycopg")
    db_user = getenv("DB_USER", "postgres")
    db_pass = getenv("DB_PASS", "")
    db_host = getenv("DB_HOST", "localhost")
    db_port = getenv("DB_PORT", "5432")
    db_database = getenv("DB_DATABASE", "postgres")
    
    # 确保端口是有效的数字
    try:
        if db_port and db_port != "None":
            int(db_port)
        else:
            db_port = "5432"
    except ValueError:
        db_port = "5432"
    
    return "{}://{}{}@{}:{}/{}".format(
        db_driver,
        db_user,
        f":{db_pass}" if db_pass else "",
        db_host,
        db_port,
        db_database,
    )

import os
from gallery import app

if __name__ == "__main__":
    app.run(host=app.config['IP'], port=app.config['PORT'])

application = app

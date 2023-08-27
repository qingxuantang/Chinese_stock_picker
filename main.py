
import threading
from importlib import reload
from qt_app import app,utils
app = reload(app)
utils = reload(utils)

config = utils.config

if __name__ == '__main__' :

    thread = threading.Thread(target=app.main())
    thread.start()
    # Run app.py for streamlit app
    #app.main()
    

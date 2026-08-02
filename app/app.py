import imaplib
import uuid
from typing import Optional

import joblib
import keras
import numpy as np
import pandas as pd
import tensorflow as tf
from fastapi import FastAPI, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import JSONResponse

from email_provider.imap import get_emails

# load the scaler since the scaler should be the SAME one used for training
scaler = joblib.load("./models/scaler.pkl")

# feature order ensures training data matches correct params
feature_order = joblib.load("./models/feature_order.pkl")

# load the model
keras.mixed_precision.set_global_policy("mixed_float16")
classifier = keras.models.load_model("./models/classifier.keras", compile=False)

app = FastAPI(title="Phishing Email Model")

# enable CORS just in case frontend runs separately during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# contain imap connection and mailbox
sessions = {}


# request for login
class LoginRequest(BaseModel):
    host: str
    username: str
    password: str
    mailbox: str = "INBOX"


@app.post("/login")
def login(request: LoginRequest, response: Response):
    try:
        imap = imaplib.IMAP4_SSL(request.host)
        imap.login(
            request.username,
            request.password
        )

        status, _ = imap.select(request.mailbox)
        if status != "OK":
            imap.logout()
            return {
                "success": False,
                "message": "Unable to open mailbox."
            }

        # create the user session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "connection": imap,
            "mailbox": request.mailbox,
        }

        # store session in browser cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=3600
        )

        return {
            "success": True,
            "email": request.username
        }
    except Exception as ex:
        if "Invalid credentials" in str(ex):
            return {
                "success": False,
                "message": "Username or password is incorrect. Please try again."
            }

        return {
            "success": False,
            "message": str(ex)
        }


# endpoint to get the emails
@app.get("/emails")
def emails(offset: int = 0, session_id: str | None = Cookie(default=None)):
    if session_id is None:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "Not logged in."
            }
        )

    session = sessions.get(
        session_id
    )

    if session is None:
        response = JSONResponse(
            status_code=401,
            content={
                "message": "Session expired."
            }
        )
        response.delete_cookie(
            "session_id"
        )
        return response

    connection = session.get("connection")
    try:
        status, _ = connection.noop()
        if status != "OK":
            raise Exception(
                "Expired connection."
            )
    except Exception:
        try:
            connection.logout()
        except Exception:
            pass

        del sessions[session_id]
        response = JSONResponse(
            status_code=401,
            content={
                "message": "Session expired."
            }
        )
        response.delete_cookie(
            "session_id"
        )
        return response

    return get_emails(
        connection=connection,
        offset=offset,
    )


# define a request format that the user will pass
class EmailRequest(BaseModel):
    subject: str
    body: str
    sender_email: str
    sender_display_name: Optional[str] = None
    sent_datetime: str


# endpoint for the prediction model
@app.post("/predict")
def predict(request: EmailRequest):
    from components.bert import preprocessor, embedding_model
    from components.numeric import extract_numeric_features
    from components.explain import explain_email
    text = (
            request.subject +
            " [SEP] " +
            request.body
    )
    tokens = preprocessor(tf.constant([text]))
    embedding = embedding_model(tokens, training=False).numpy()

    numeric_features = extract_numeric_features(request)
    numeric = pd.DataFrame([numeric_features])
    numeric = numeric[feature_order]
    numeric = scaler.transform(numeric)

    features = np.concatenate(
        [
            embedding,
            numeric
        ],
        axis=1
    )
    prediction = classifier(
        features,
        training=False
    ).numpy()

    predicted_class = int(np.argmax(prediction))
    confidence = float(
        prediction[0][predicted_class]
    )

    analysis = explain_email(request)

    return {
        "prediction": predicted_class,
        "confidence": confidence,
        "analysis": analysis,
    }


@app.post("/logout")
def logout(response: Response, session_id: str | None = Cookie(default=None)):
    if session_id is None:
        return {
            "success": True
        }

    session = sessions.get(session_id)
    if session is not None:
        connection = session.get("connection")
        if connection is not None:
            try:
                connection.logout()
            except Exception:
                pass

        sessions.pop(
            session_id,
            None
        )

    response.delete_cookie(
        "session_id"
    )

    return {
        "success": True
    }


@app.get("/")
def connection_page():
    return FileResponse(
        "templates/index.html"
    )


@app.get("/inbox")
def inbox_page(session_id: str | None = Cookie(default=None)):
    if session_id is None:
        return RedirectResponse(
            "/",
            status_code=302
        )

    if session_id not in sessions:
        return RedirectResponse(
            "/",
            status_code=302
        )

    return FileResponse(
        "templates/inbox.html"
    )


# Mount the static folder so the frontend HTML/CSS/JS is served directly by FastAPI
app.mount("/static", StaticFiles(directory="static"), name="static")

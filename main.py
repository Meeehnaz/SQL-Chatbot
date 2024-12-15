from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from endpoints.new_api import router as chatbot_router
from route import router as chatbot_router
# from new import router as chatbot_router


app = FastAPI()

origins = [
    'https://day-front.graywave-c8c0d7b3.uaenorth.azurecontainerapps.io',
    'http://localhost:3000'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(chatbot_router)


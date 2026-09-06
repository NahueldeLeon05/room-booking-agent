# Architecture

## Overview

CUBO is separated into small layers with one responsibility each. The model is
only the conversational interface. If the chatbot were removed, the booking
service and its rules would still work.

## Layers

- **Streamlit UI:** shows the login and sends the conversation to the API.
- **FastAPI:** authenticates the user and creates the dependencies for each
  request.
- **LangGraph agent:** decides when a tool is needed and returns the final text.
- **Tools:** translate model arguments into service calls.
- **Service:** coordinates business rules and persistence.
- **Domain:** contains entities, time ranges, and pure validation functions.
- **Repository:** maps domain entities to SQLAlchemy models and runs database
  operations.
- **SQLite:** stores users, rooms, bookings, and the slots used for concurrency
  control.

## Component diagram

The complete component diagram is in the
[project overview](00-overview.md#component-diagram). It is kept in one place
so there are not two copies to maintain.

## Request flow

1. The user sends a message from Streamlit with the JWT and conversation
   history.
2. FastAPI decodes the token and obtains the authenticated user.
3. The API builds the repository, service, tools, and graph for that request.
   The authenticated `user_id` is captured by the tools.
4. LangGraph sends the messages and tool schemas to the model.
5. The model returns either a final answer or the intention to call a tool. It
   never executes Python or accesses the database directly.
6. A tool calls the service. The service validates the request and the
   repository reads or writes the database.
7. The tool result returns to the model as text, and the final answer returns
   to Streamlit.

## Dependency direction

Dependencies point toward the domain. The API and tools know the service, and
the infrastructure implements the repository used by the service. The domain
does not import FastAPI, SQLAlchemy, LangGraph, or OpenAI.

This keeps the business rules independent from the interface and the database.
It also allows domain and service tests to run without starting the API or
calling a model.

## Presentation layer

I used Streamlit because it was the fastest way to build a working
conversational interface for the challenge. The API does not depend on
Streamlit, so another client could replace it without changing the domain or
service.

The conversation uses text instead of cards or time-slot buttons. I wanted the
user to complete the booking by writing, not by using a form with a chat placed
on top.

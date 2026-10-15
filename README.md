# Candidate Communication Platform

The application allows recruiters to manage candidates, send individual and bulk messages, track delivery statuses, handle failures, and view communication history.

## Tech Stack

### Frontend
- React.js
- Next.js
- TypeScript
- Material UI

### Backend
- Python
- Django
- Django REST Framework

## Features

- Add candidates
- View candidate list
- Search candidates
- Delete candidates
- Bulk delete candidates
- View candidate communication history
- Send individual messages
- Send bulk messages
- Track message delivery status
- Handle failed messages
- Retry failed messages
- Form validation
- API error handling
- Responsive user interface

## Architecture

The application follows a frontend and backend architecture.

### Frontend

The frontend is built using Next.js, React.js, TypeScript, and Material UI.

It communicates with the Django REST API through HTTP requests.

### Backend

The backend is built using Django and Django REST Framework.

It provides REST APIs for candidate management and communication-related operations.

### Communication Provider

A dummy communication provider is used to simulate message delivery.

This allows the application to demonstrate sending messages, delivery statuses, and failure handling without depending on an external messaging service.

## Project Structure

```text
Assignment/
├── backend/
│   ├── candidates/
│   ├── config/
│   ├── manage.py
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── .gitignore
└── README.md

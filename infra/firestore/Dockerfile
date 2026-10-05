# Uses the official Firebase CLI image — actively maintained, multi-arch (amd64 + arm64)
# Starts only the Firestore emulator, bound to 0.0.0.0 so other containers can reach it.
FROM node:20-alpine

# Install the Firebase CLI globally
RUN npm install -g firebase-tools

WORKDIR /firebase

# Copy emulator config
COPY firebase.json .
COPY firestore.rules .
COPY firestore.indexes.json .

# Warm up: pre-download the Firestore emulator JAR at build time so startup is fast
# The JAR is cached in /root/.cache/firebase/emulators/
RUN firebase setup:emulators:firestore

EXPOSE 8080

ENV FIRESTORE_PROJECT_ID=workflow-platform-dev

CMD ["firebase", "emulators:start", "--only", "firestore", "--project", "workflow-platform-dev"]

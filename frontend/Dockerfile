FROM node:20-alpine
WORKDIR /app
RUN echo '{"name":"frontend","scripts":{"start":"npx serve -s . -l 3000"}}' > package.json
RUN npm install serve
CMD ["npm", "start"]

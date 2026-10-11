# Beemer API. Build from backend/: docker build -t beemer-api backend
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
COPY src src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21-jre
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /src/target/beemer-api-1.0.0.jar app.jar
ENV PORT=8080 \
    BEEMER_DATA_DIR=/data \
    BEEMER_BOOTSTRAP_FALLBACK=none
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=5 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/actuator/health" | grep -q UP
ENTRYPOINT ["java", "-jar", "/app/app.jar"]

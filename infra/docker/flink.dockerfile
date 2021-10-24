FROM maven:3.8-openjdk-8 as build
WORKDIR /app
COPY . /app
RUN mvn package

FROM flink:1.13.2-scala_2.12
COPY --from=build /app/target /flink-web-upload
CMD ["help"]
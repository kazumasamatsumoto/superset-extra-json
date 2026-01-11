import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Enable CORS for Angular frontend
  app.enableCors({
    origin: 'http://localhost:4200',
    credentials: true,
  });

  const port = process.env.PORT ?? 3001;

  await app.listen(port);
  console.log(`Nest.js backend running on http://localhost:${port}`);
}
bootstrap();

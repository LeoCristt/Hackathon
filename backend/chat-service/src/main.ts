import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Включаем CORS для WebSocket соединений
  app.enableCors({
    origin: '*',
    credentials: true,
  });

  const port = process.env.PORT ?? 3001;
  await app.listen(port);

  console.log(`🚀 Chat Service запущен на порту ${port}`);
  console.log(`🔌 WebSocket сервер готов к подключениям`);
}
bootstrap();

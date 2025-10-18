import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { ChatGateway } from './chat.gateway';
import { RabbitMQService } from './rabbitmq.service';
import { RedisService } from './redis.service';

@Module({
  imports: [],
  controllers: [AppController],
  providers: [AppService, ChatGateway, RabbitMQService, RedisService],
})
export class AppModule {}

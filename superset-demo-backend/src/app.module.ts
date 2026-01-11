import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { SupersetModule } from './superset/superset.module';

@Module({
  imports: [SupersetModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}

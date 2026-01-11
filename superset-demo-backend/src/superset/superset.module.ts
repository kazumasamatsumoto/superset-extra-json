import { Module } from '@nestjs/common';
import { SupersetController } from './superset.controller';
import { SupersetService } from './superset.service';

@Module({
  controllers: [SupersetController],
  providers: [SupersetService],
})
export class SupersetModule {}

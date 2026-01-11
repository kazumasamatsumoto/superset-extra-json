import { Controller, Get, Query } from '@nestjs/common';
import { SupersetService } from './superset.service';

@Controller('api/superset')
export class SupersetController {
  constructor(private readonly supersetService: SupersetService) {}

  @Get('guest-token')
  getGuestToken(
    @Query('departmentId') departmentId: string,
    @Query('username') username: string,
  ) {
    const deptId = parseInt(departmentId, 10);
    const user = username || `部署${deptId}ユーザー`;

    const token = this.supersetService.generateGuestToken(deptId, user);
    const dashboardUrl = this.supersetService.getDashboardUrl(token);

    return {
      token,
      dashboardUrl,
      departmentId: deptId,
      username: user,
    };
  }

  @Get('departments')
  getDepartments() {
    return [
      { id: 101, name: '営業部', expectedTotal: '¥955,000' },
      { id: 102, name: '開発部', expectedTotal: '¥835,000' },
      { id: 103, name: 'マーケティング部', expectedTotal: '¥240,000' },
    ];
  }
}

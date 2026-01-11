import { Injectable } from '@nestjs/common';
import * as jwt from 'jsonwebtoken';

@Injectable()
export class SupersetService {
  private readonly SUPERSET_SECRET_KEY = 'TEST_NON_DEV_SECRET';
  private readonly SUPERSET_URL = 'http://localhost:8088';
  private readonly DASHBOARD_ID = '12';
  private readonly EMBEDDED_DASHBOARD_UUID = '7aaabc03-2c47-4540-8233-f22bbdb2cc81';

  generateGuestToken(departmentId: number, username: string): string {
    const now = Math.floor(Date.now() / 1000);
    const payload = {
      user: {
        username,
        first_name: 'Guest',
        last_name: 'User',
        extra_json: {
          target_department_id: departmentId,  // Pass department_id via extra_json instead of RLS
        },
      },
      resources: [
        {
          type: 'dashboard',
          id: this.EMBEDDED_DASHBOARD_UUID,
        },
      ],
      rls_rules: [
        {
          clause: `department_id = ${departmentId}`  // Test: Use RLS to see actual SQL execution
        }
      ],
      // Standard JWT claims
      iat: now,  // issued at
      exp: now + 86400,  // expiration time (24 hours)
      aud: 'http://superset:8088/',  // audience - Superset domain (must match WEBDRIVER_BASEURL)
      type: 'guest',
    };

    return jwt.sign(payload, this.SUPERSET_SECRET_KEY, { algorithm: 'HS256' });
  }

  getDashboardUrl(guestToken: string): string {
    return `${this.SUPERSET_URL}/dashboard/${this.DASHBOARD_ID}/embedded`;
  }
}

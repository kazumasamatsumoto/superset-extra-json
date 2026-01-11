import { Component, OnInit, OnDestroy, ElementRef, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { embedDashboard } from '@superset-ui/embedded-sdk';

interface Department {
  id: number;
  name: string;
  expectedTotal: string;
}

interface GuestTokenResponse {
  token: string;
  dashboardUrl: string;
  departmentId: number;
  username: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container">
      <h1>Superset 5.0 動的フィルタリング検証 (Embedded SDK)</h1>

      <div class="info">
        <strong>検証内容:</strong> Dataset Extra JSON + Jinja Template + Guest Token RLS による部署別フィルタリング<br>
        <strong>実装方法:</strong> Superset Embedded SDK + Nest.js + Angular
      </div>

      <div class="tabs">
        <button
          *ngFor="let dept of departments"
          [class.active]="selectedDepartment?.id === dept.id"
          (click)="loadDepartment(dept)"
          class="tab-button">
          {{ dept.name }} (ID: {{ dept.id }})
        </button>
      </div>

      <div class="dashboard-container">
        <div #dashboardContainer id="superset-dashboard"></div>
      </div>

      <div class="expected-total" *ngIf="selectedDepartment">
        期待される売上合計: <strong>{{ selectedDepartment.expectedTotal }}</strong> ({{ selectedDepartment.name }})
      </div>
    </div>
  `,
  styles: [`
    .container {
      max-width: 1400px;
      margin: 0 auto;
      padding: 20px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    h1 {
      color: #333;
      margin-bottom: 10px;
      font-size: 24px;
    }

    .info {
      background: #e3f2fd;
      border-left: 4px solid #2196F3;
      padding: 15px;
      margin-bottom: 20px;
      border-radius: 4px;
    }

    .tabs {
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
      border-bottom: 2px solid #ddd;
      padding-bottom: 10px;
    }

    .tab-button {
      padding: 10px 20px;
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 4px 4px 0 0;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: all 0.3s;
    }

    .tab-button:hover {
      background: #f5f5f5;
    }

    .tab-button.active {
      background: #2196F3;
      color: white;
      border-color: #2196F3;
    }

    .dashboard-container {
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      overflow: hidden;
      min-height: 1400px;
    }

    #superset-dashboard {
      width: 100%;
      min-height: 1400px;
    }

    :host ::ng-deep #superset-dashboard iframe {
      width: 100% !important;
      height: 1400px !important;
      min-height: 1400px !important;
    }

    :host ::ng-deep iframe {
      width: 100% !important;
      height: 1400px !important;
    }

    .expected-total {
      margin-top: 15px;
      padding: 10px 15px;
      background: #f9f9f9;
      border-radius: 4px;
      font-size: 14px;
    }

    .expected-total strong {
      color: #2196F3;
    }
  `]
})
export class DashboardComponent implements OnInit, OnDestroy {
  @ViewChild('dashboardContainer', { static: true }) dashboardContainer!: ElementRef;

  departments: Department[] = [];
  selectedDepartment: Department | null = null;
  private currentEmbed: any = null;

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadDepartments();
  }

  ngOnDestroy() {
    if (this.currentEmbed) {
      // Clean up the embedded dashboard
      const container = document.getElementById('superset-dashboard');
      if (container) {
        container.innerHTML = '';
      }
    }
  }

  loadDepartments() {
    this.http.get<Department[]>('http://localhost:3001/api/superset/departments')
      .subscribe({
        next: (departments) => {
          this.departments = departments;
          this.cdr.detectChanges(); // Force change detection
          console.log('Departments loaded:', this.departments.length);
          if (departments.length > 0) {
            this.loadDepartment(departments[0]);
          }
        },
        error: (error) => {
          console.error('Failed to load departments:', error);
        }
      });
  }

  async loadDepartment(department: Department) {
    this.selectedDepartment = department;

    // Unmount previous embed completely
    if (this.currentEmbed && this.currentEmbed.unmount) {
      try {
        await this.currentEmbed.unmount();
      } catch (e) {
        console.log('Error unmounting previous embed:', e);
      }
    }

    // Clear container
    const container = document.getElementById('superset-dashboard');
    if (container) {
      container.innerHTML = '';
    }

    try {
      // Get guest token from backend
      const response = await this.http.get<GuestTokenResponse>(
        `http://localhost:3001/api/superset/guest-token?departmentId=${department.id}&username=${department.name}ユーザー`
      ).toPromise();

      if (!response) {
        throw new Error('Failed to get guest token');
      }

      console.log('Guest token received for', department.name, '- Department ID:', department.id);

      // Small delay to ensure clean unmount
      await new Promise(resolve => setTimeout(resolve, 100));

      // Embed dashboard using Superset SDK with fresh token
      this.currentEmbed = await embedDashboard({
        id: '7aaabc03-2c47-4540-8233-f22bbdb2cc81', // embedded dashboard UUID
        supersetDomain: 'http://localhost:8088',
        mountPoint: container!,
        fetchGuestToken: async () => response.token,
        dashboardUiConfig: {
          hideTitle: false,
          hideChartControls: false,
          hideTab: false,
        },
      });

      console.log('Dashboard embedded successfully for', department.name);
    } catch (error) {
      console.error('Failed to embed dashboard:', error);
      if (container) {
        container.innerHTML = `<div style="padding: 20px; color: red;">Failed to load dashboard: ${error}</div>`;
      }
    }
  }
}

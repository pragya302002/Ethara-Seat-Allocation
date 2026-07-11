export type UserRole = "admin" | "hr" | "project_manager" | "employee";
export type EmploymentStatus = "active" | "on_leave" | "terminated" | "notice_period";
export type SeatType = "standard" | "standing_desk" | "cabin" | "meeting_pod" | "accessible";
export type SeatStatus = "vacant" | "occupied" | "reserved" | "out_of_service";

export interface Employee {
  id: string;
  employee_code: string;
  full_name: string;
  email: string;
  department_id: string | null;
  designation: string;
  manager_id: string | null;
  employment_status: EmploymentStatus;
  date_of_joining: string;
  location: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmployeePage {
  items: Employee[];
  total: number;
  page: number;
  page_size: number;
}

export interface Seat {
  id: string;
  seat_number: string;
  zone_id: string;
  row_label: string | null;
  seat_type: SeatType;
  status: SeatStatus;
}

export interface OccupancySummary {
  vacant: number;
  occupied: number;
  reserved: number;
  out_of_service: number;
  total: number;
  utilization_percent: number;
}

export interface Project {
  id: string;
  name: string;
  code: string;
  client: string;
  manager_id: string | null;
  team_size_target: number;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectPage {
  items: Project[];
  total: number;
  page: number;
  page_size: number;
}

export interface DepartmentCount {
  department: string;
  count: number;
}

export interface ProjectCount {
  project: string;
  count: number;
}

export interface FloorUtilization {
  building: string;
  floor: number;
  total_seats: number;
  occupied_seats: number;
  utilization_percent: number;
}

export interface RecentAllocationItem {
  id: string;
  seat_id: string;
  employee_id: string;
  event_type: string;
  allocation_date: string;
  release_date: string | null;
}

export interface DashboardSummary {
  total_employees: number;
  new_joiners_last_30_days: number;
  occupancy: OccupancySummary;
  department_wise: DepartmentCount[];
  project_wise: ProjectCount[];
  floor_utilization: FloorUtilization[];
  recent_allocations: RecentAllocationItem[];
  recent_releases: RecentAllocationItem[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  employee_id: string;
  full_name: string;
}

export interface AssistantResponse {
  answer: string;
  query_understood: boolean;
}

import { api } from "@/lib/api";
import {
  DashboardSummary,
  Employee,
  EmployeePage,
  ProjectPage,
  Seat,
  AssistantResponse,
} from "@/types";

export const employeeService = {
  list: (params: { q?: string; page?: number; page_size?: number }) =>
    api.get<EmployeePage>("/employees", { params }).then((r) => r.data),
  withoutSeat: (params: { page?: number; page_size?: number }) =>
    api.get<EmployeePage>("/employees/without-seat", { params }).then((r) => r.data),
  get: (id: string) => api.get<Employee>(`/employees/${id}`).then((r) => r.data),
};

export const seatService = {
  vacant: (params?: { zone_id?: string; floor_id?: string }) =>
    api.get<Seat[]>("/seats/vacant", { params }).then((r) => r.data),
  allocate: (payload: { seat_id: string; employee_id: string }) =>
    api.post("/seats/allocate", payload).then((r) => r.data),
  release: (payload: { seat_id: string }) => api.post("/seats/release", payload).then((r) => r.data),
  transfer: (payload: { employee_id: string; new_seat_id: string }) =>
    api.post("/seats/transfer", payload).then((r) => r.data),
  history: (seatId: string) => api.get(`/seats/${seatId}/history`).then((r) => r.data),
};

export const projectService = {
  list: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number }) =>
    api.get<ProjectPage>("/projects", { params }).then((r) => r.data),
};

export const dashboardService = {
  summary: () => api.get<DashboardSummary>("/dashboard/summary").then((r) => r.data),
};

export const assistantService = {
  ask: (question: string) =>
    api.post<AssistantResponse>("/assistant/query", { question }).then((r) => r.data),
};

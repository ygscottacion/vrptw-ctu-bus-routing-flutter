export type User = { id: number; username: string; full_name?: string; phone?: string; role: string };
export type Vehicle = { id: number; license_plate: string; capacity: number; driver?: User; driver_id?: number };
export type Incident = { id: number; title: string; description?: string; status: string; reported_at: string; driver?: User };
export type BusLocation = { vehicle_id: number; license_plate?: string; latitude: number; longitude: number; speed?: number; status?: string };
export type Location = { id: number; name: string; latitude: number; longitude: number; demand?: number; time_window_start?: string; time_window_end?: string; };

declare global {
  interface Window {
    L: any;
  }
}
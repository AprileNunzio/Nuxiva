export interface WidgetGridSpan {
  col: number;
  row: number;
}

export interface WidgetItem {
  id: string;
  name: string;
  category: string;
  description: string;
  icon: string;
  render_type: "metric" | "grid" | "card" | "canvas" | "toggle" | "graph" | string;
  grid_span: WidgetGridSpan;
  state: Record<string, any>;
}

export interface WidgetActionPayload {
  action: string;
  payload?: Record<string, any>;
}

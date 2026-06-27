export type AsyncStatus = "loading" | "success" | "error";

export interface AsyncState<T> {
  status: AsyncStatus;
  data: T;
  error: string | null;
}

export const initialAsyncState = <T>(data: T): AsyncState<T> => ({
  status: "loading",
  data,
  error: null,
});

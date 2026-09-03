import type {
  LoginCredentials,
  RegisterInput,
  RegisterResponse,
  TokenResponse,
  AuthMeResponse,
  ProfilePublic,
} from "@/types/auth";
import {
  healthcoreRequest,
  setAccessToken,
} from "@/lib/services/healthcoreClient";
import { track } from "@/lib/services/telemetry";

export async function forgotPassword(email: string): Promise<{ message: string }> {
  return healthcoreRequest<{ message: string }>("/auth/forgot-password", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(input: {
  token: string;
  newPassword: string;
}): Promise<{ message: string }> {
  return healthcoreRequest<{ message: string }>("/auth/reset-password", {
    method: "POST",
    auth: false,
    body: JSON.stringify({
      token: input.token,
      new_password: input.newPassword,
    }),
  });
}

export async function changePassword(input: {
  currentPassword: string;
  newPassword: string;
}): Promise<{ message: string }> {
  return healthcoreRequest<{ message: string }>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: input.currentPassword,
      new_password: input.newPassword,
    }),
  });
}

export async function login(credentials: LoginCredentials): Promise<TokenResponse> {
  const token = await healthcoreRequest<TokenResponse>("/auth/login", {
    method: "POST",
    auth: false,
    body: JSON.stringify({
      username: credentials.email,
      password: credentials.password,
      grant_type: "password",
    }),
  });
  setAccessToken(token.access_token);
  track("login_succeeded", {});
  return token;
}

export async function register(input: RegisterInput): Promise<RegisterResponse> {
  return healthcoreRequest<RegisterResponse>("/users", {
    method: "POST",
    auth: false,
    body: JSON.stringify({
      email: input.email,
      password: input.password,
      ...(input.name?.trim() ? { name: input.name.trim() } : {}),
      ...(input.phone?.trim() ? { phone: input.phone.trim() } : {}),
      ...(input.address?.trim() ? { address: input.address.trim() } : {}),
    }),
  });
}

/** Register then login with the same credentials; stores the JWT. */
export async function registerAndLogin(
  input: RegisterInput
): Promise<TokenResponse> {
  await register(input);
  return login({ email: input.email, password: input.password });
}

export function fetchCurrentUser(): Promise<AuthMeResponse> {
  return healthcoreRequest<AuthMeResponse>("/auth/me");
}

export function updateMyProfile(input: {
  name?: string | null;
  phone?: string | null;
  address?: string | null;
}): Promise<ProfilePublic> {
  return healthcoreRequest<ProfilePublic>("/profiles/me", {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

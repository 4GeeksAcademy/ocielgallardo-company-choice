import type {
  LoginCredentials,
  RegisterInput,
  TokenResponse,
  UserPublic,
  AuthMeResponse,
  ProfilePublic,
} from "@/types/auth";
import {
  healthcoreRequest,
  setAccessToken,
} from "@/lib/services/healthcoreClient";

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
  return token;
}

export async function register(input: RegisterInput): Promise<UserPublic> {
  return healthcoreRequest<UserPublic>("/users", {
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

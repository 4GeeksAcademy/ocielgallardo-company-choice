export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterInput {
  email: string;
  password: string;
  name?: string;
  phone?: string;
  address?: string;
}

export interface UserPublic {
  id: number;
  email: string;
  is_active: boolean;
  role: string;
  created_at: string;
}

/** POST /users — no email or credentials in the body. */
export interface RegisterResponse {
  id: number;
  is_active: boolean;
  role: string;
  created_at: string;
}

export interface ProfilePublic {
  id: number;
  user_id: number;
  name: string | null;
  phone: string | null;
  address: string | null;
}

export interface AuthMeResponse {
  email: string;
  role: string;
  profile: ProfilePublic | null;
}

export interface ForgotPasswordResponse {
  message: string;
}

export interface ResetPasswordResponse {
  message: string;
}

export interface ChangePasswordResponse {
  message: string;
}

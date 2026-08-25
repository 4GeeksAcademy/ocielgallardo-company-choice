import { ForgotPasswordForm } from "@/components/forms/ForgotPasswordForm";
import { AuthPageShell } from "@/components/layout/AuthPageShell";

export default function ForgotPasswordPage() {
  return (
    <AuthPageShell
      title="Restablecer contraseña"
      description="Introduce tu email y te enviaremos un enlace para crear una nueva contraseña."
    >
      <ForgotPasswordForm />
    </AuthPageShell>
  );
}

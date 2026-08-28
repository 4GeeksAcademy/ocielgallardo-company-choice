"use client";

import { useCallback, useState } from "react";

export function useFormSubmit() {
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const clearMessages = useCallback(() => {
    setError(null);
    setSuccess(null);
  }, []);

  const runSubmit = useCallback(async (submit: () => Promise<void>) => {
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);
    try {
      await submit();
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  return {
    error,
    setError,
    success,
    setSuccess,
    isSubmitting,
    setIsSubmitting,
    clearMessages,
    runSubmit,
  };
}

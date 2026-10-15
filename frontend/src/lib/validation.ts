import type { CandidateInput } from "@/types";

/** Mirrors the backend limits in candidates/serializers.py. */
export const MESSAGE_MAX_LENGTH = 1600;
export const BULK_MAX_RECIPIENTS = 500;
const PHONE_ALLOWED_CHARS = /^\+?[\d\s\-().]+$/;
const PHONE_MIN_DIGITS = 7;
const PHONE_MAX_DIGITS = 15;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export type CandidateFormErrors = Partial<Record<keyof CandidateInput | "non_field_errors", string>>;

export function validateCandidate(input: CandidateInput): CandidateFormErrors {
  const errors: CandidateFormErrors = {};

  const name = input.name.trim();
  if (!name) errors.name = "Name is required.";
  else if (name.length > 255) errors.name = "Name must be at most 255 characters.";

  const email = input.email.trim();
  if (!email) errors.email = "Email is required.";
  else if (!EMAIL_PATTERN.test(email)) errors.email = "Enter a valid email address.";

  const phone = input.phone.trim();
  const digits = phone.replace(/\D/g, "").length;
  if (!phone) errors.phone = "Phone is required.";
  else if (!PHONE_ALLOWED_CHARS.test(phone))
    errors.phone = 'Use only digits, spaces, hyphens, dots, parentheses and an optional leading "+".';
  else if (digits < PHONE_MIN_DIGITS || digits > PHONE_MAX_DIGITS)
    errors.phone = `Phone must contain between ${PHONE_MIN_DIGITS} and ${PHONE_MAX_DIGITS} digits.`;
  else if (phone.length > 20) errors.phone = "Phone must be at most 20 characters.";

  return errors;
}

export function validateMessageBody(body: string): string | null {
  if (!body.trim()) return "Message cannot be empty.";
  if (body.trim().length > MESSAGE_MAX_LENGTH) {
    return `Message must be at most ${MESSAGE_MAX_LENGTH} characters.`;
  }
  return null;
}

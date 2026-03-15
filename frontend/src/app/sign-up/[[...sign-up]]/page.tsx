import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="relative flex items-center justify-center min-h-[70vh]">
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-120 h-60 bg-linear-to-r from-accent/20 via-primary/10 to-secondary/15 rounded-full blur-3xl" />
      </div>
      <SignUp />
    </div>
  );
}

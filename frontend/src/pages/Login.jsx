import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { LogIn, Mail, Lock } from "lucide-react";
import Alert from "../components/Alert.jsx";
import AuthLayout from "../components/auth/AuthLayout.jsx";
import Button from "../components/Button.jsx";
import Input from "../components/Input.jsx";
import useAuth from "../hooks/useAuth.js";

function validate({ email, password }) {
  const errors = {};

  if (!email.trim()) errors.email = "Enter your email address.";
  if (!password) errors.password = "Enter your password.";

  return errors;
}

function Login() {
  const { user, isLoading, login } = useAuth();
  const location = useLocation();
  const from = location.state?.from?.pathname ?? "/";

  const [values, setValues] = useState({ email: "", password: "" });
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const errors = submitted ? validate(values) : {};

  function handleChange(e) {
    const { name, value } = e.target;
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitted(true);
    setSubmitError(null);

    if (Object.keys(validate(values)).length > 0) return;

    setIsSubmitting(true);
    try {
      await login(values.email.trim(), values.password);
    } catch (err) {
      setSubmitError(err.message);
      setIsSubmitting(false);
    }
  }

  if (isLoading) return null;
  if (user) return <Navigate to={from} replace />;

  return (
    <AuthLayout
      title="Sign in"
      subtitle="Use your clinic account to start screening."
    >
      {submitError && <Alert title="Could not sign in">{submitError}</Alert>}

      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <Input
          label="Email"
          name="email"
          type="email"
          icon={Mail}
          autoComplete="email"
          value={values.email}
          onChange={handleChange}
          error={errors.email}
        />
        <Input
          label="Password"
          name="password"
          type="password"
          icon={Lock}
          autoComplete="current-password"
          value={values.password}
          onChange={handleChange}
          error={errors.password}
        />
        <Button type="submit" icon={LogIn} fullWidth disabled={isSubmitting}>
          {isSubmitting ? "Signing in" : "Sign in"}
        </Button>
      </form>
    </AuthLayout>
  );
}

export default Login;

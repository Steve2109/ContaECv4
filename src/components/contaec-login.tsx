'use client';

import Image from 'next/image';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  Shield,
  FileText,
  Check,
  X,
} from 'lucide-react';
import { login, register, type User } from '@/lib/api';
import { t } from '@/lib/i18n';

interface ContaECLoginProps {
  onAuthSuccess: (user: User) => void;
}

export function ContaECLogin({ onAuthSuccess }: ContaECLoginProps) {
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Login form state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register form state
  const [regFullName, setRegFullName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');

  // Password strength requirements (normativa de contraseña segura)
  const passwordRequirements = [
    { key: 'min', label: t('login.password_req_min'), ok: regPassword.length >= 8 },
    { key: 'upper', label: t('login.password_req_upper'), ok: /[A-Z]/.test(regPassword) },
    { key: 'lower', label: t('login.password_req_lower'), ok: /[a-z]/.test(regPassword) },
    { key: 'number', label: t('login.password_req_number'), ok: /\d/.test(regPassword) },
    { key: 'symbol', label: t('login.password_req_symbol'), ok: /[^A-Za-z0-9\s]/.test(regPassword) },
  ];
  const passwordValid = passwordRequirements.every((r) => r.ok);
  const passwordsMatch = regConfirmPassword === '' || regPassword === regConfirmPassword;

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const { user } = await login(loginEmail, loginPassword);
      onAuthSuccess(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('login.login_error'));
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // Validar normativa de contraseña antes de enviar
    if (!passwordValid) {
      setError(t('login.password_requirements'));
      return;
    }
    if (regPassword !== regConfirmPassword) {
      setError(t('login.passwords_dont_match'));
      return;
    }

    setLoading(true);

    try {
      const { user } = await register({
        email: regEmail,
        password: regPassword,
        confirm_password: regConfirmPassword,
        full_name: regFullName,
      });
      onAuthSuccess(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('login.register_error'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <main className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-md">
          {/* Logo & Branding */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 mb-4">
              <Image
                src="/logo.svg"
                alt="ContaEC Logo"
                width={80}
                height={80}
                className="h-20 w-20"
                priority
              />
            </div>
            <h1 className="text-3xl font-bold text-foreground tracking-tight">
              ContaEC
            </h1>
            <p className="text-muted-foreground mt-1 text-sm">
              {t('login.tagline')}
            </p>
          </div>

          {/* Login/Register Card */}
          <Card className="shadow-lg border-border/50">
            <CardHeader className="pb-4">
              <Tabs
                value={activeTab}
                onValueChange={(v) => {
                  setActiveTab(v as 'login' | 'register');
                  setError(null);
                }}
              >
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="login">{t('login.tab_login')}</TabsTrigger>
                  <TabsTrigger value="register">{t('login.tab_register')}</TabsTrigger>
                </TabsList>

                {/* Login Tab */}
                <TabsContent value="login" className="mt-4">
                  <CardTitle className="text-xl">{t('login.welcome_back')}</CardTitle>
                  <CardDescription>
                    {t('login.credentials_desc')}
                  </CardDescription>
                </TabsContent>

                {/* Register Tab */}
                <TabsContent value="register" className="mt-4">
                  <CardTitle className="text-xl">{t('login.create_account')}</CardTitle>
                  <CardDescription>
                    {t('login.register_desc')}
                  </CardDescription>
                </TabsContent>
              </Tabs>
            </CardHeader>

            <CardContent>
              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Login Form */}
              {activeTab === 'login' && (
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email">{t('login.email_label')}</Label>
                    <Input
                      id="login-email"
                      type="email"
                      placeholder="usuario@empresa.com"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      required
                      autoComplete="email"
                      disabled={loading}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password">{t('login.password_label')}</Label>
                    <div className="relative">
                      <Input
                        id="login-password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder={t('login.password_placeholder')}
                        value={loginPassword}
                        onChange={(e) => setLoginPassword(e.target.value)}
                        required
                        autoComplete="current-password"
                        disabled={loading}
                        className="pr-10"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                        onClick={() => setShowPassword(!showPassword)}
                        tabIndex={-1}
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <Eye className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                    </div>
                  </div>
                  <Button type="submit" className="w-full" disabled={loading}>
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        {t('login.signing_in')}
                      </>
                    ) : (
                      t('login.sign_in')
                    )}
                  </Button>
                </form>
              )}

              {/* Register Form */}
              {activeTab === 'register' && (
                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="reg-name">{t('login.full_name')}</Label>
                    <Input
                      id="reg-name"
                      type="text"
                      placeholder="Juan Perez"
                      value={regFullName}
                      onChange={(e) => setRegFullName(e.target.value)}
                      required
                      disabled={loading}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="reg-email">{t('login.email_label')}</Label>
                    <Input
                      id="reg-email"
                      type="email"
                      placeholder="usuario@empresa.com"
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      required
                      autoComplete="email"
                      disabled={loading}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="reg-password">{t('login.password_label')}</Label>
                    <div className="relative">
                      <Input
                        id="reg-password"
                        type={showRegPassword ? 'text' : 'password'}
                        placeholder={t('login.min_chars')}
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        required
                        minLength={8}
                        autoComplete="new-password"
                        disabled={loading}
                        className="pr-10"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                        onClick={() => setShowRegPassword(!showRegPassword)}
                        tabIndex={-1}
                      >
                        {showRegPassword ? (
                          <EyeOff className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <Eye className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="reg-confirm-password">{t('login.confirm_password')}</Label>
                    <Input
                      id="reg-confirm-password"
                      type="password"
                      placeholder={t('login.repeat_password')}
                      value={regConfirmPassword}
                      onChange={(e) => setRegConfirmPassword(e.target.value)}
                      required
                      minLength={8}
                      autoComplete="new-password"
                      disabled={loading}
                      className={regConfirmPassword && !passwordsMatch ? 'border-destructive' : ''}
                    />
                    {regConfirmPassword && !passwordsMatch && (
                      <p className="text-xs text-destructive">{t('login.passwords_dont_match')}</p>
                    )}
                  </div>

                  {/* Checklist de requisitos de contraseña */}
                  <div className="rounded-md border bg-muted/40 p-3 space-y-1.5">
                    <p className="text-xs font-medium text-muted-foreground">{t('login.password_requirements_title')}</p>
                    {passwordRequirements.map((req) => (
                      <div key={req.key} className="flex items-center gap-2 text-xs">
                        {req.ok ? (
                          <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                        ) : (
                          <X className="h-3.5 w-3.5 text-destructive shrink-0" />
                        )}
                        <span className={req.ok ? 'text-emerald-700 dark:text-emerald-400' : 'text-muted-foreground'}>
                          {req.label}
                        </span>
                      </div>
                    ))}
                  </div>

                  <Button type="submit" className="w-full" disabled={loading}>
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        {t('login.creating')}
                      </>
                    ) : (
                      t('login.create')
                    )}
                  </Button>
                </form>
              )}
            </CardContent>
          </Card>

          {/* Feature highlights */}
          <div className="mt-8 grid grid-cols-3 gap-4 text-center">
            <div className="flex flex-col items-center gap-1.5">
              <div className="rounded-lg bg-primary/10 p-2">
                <Shield className="h-4 w-4 text-primary" />
              </div>
              <span className="text-xs text-muted-foreground">
                {t('login.sri_compliance')}
              </span>
            </div>
            <div className="flex flex-col items-center gap-1.5">
              <div className="rounded-lg bg-primary/10 p-2">
                <FileText className="h-4 w-4 text-primary" />
              </div>
              <span className="text-xs text-muted-foreground">
                {t('login.electronic_invoicing')}
              </span>
            </div>
            <div className="flex flex-col items-center gap-1.5">
              <div className="rounded-lg bg-primary/10 p-1.5">
                <Image
                  src="/logo.svg"
                  alt="ContaEC"
                  width={20}
                  height={20}
                  className="h-4 w-4"
                />
              </div>
              <span className="text-xs text-muted-foreground">
                {t('login.accounting')}
              </span>
            </div>
          </div>
        </div>
      </main>

      {/* Sticky Footer */}
      <footer className="border-t bg-card py-4 px-4 text-center">
        <p className="text-xs text-muted-foreground">
          {t('login.developed_by')} <span className="font-semibold text-foreground">T&amp;M Technology Ec</span>
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          info@tymtechnology.shop &nbsp;|&nbsp; 0960068866
        </p>
      </footer>
    </div>
  );
}

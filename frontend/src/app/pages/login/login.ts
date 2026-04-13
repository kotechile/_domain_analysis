import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { SupabaseService } from '../../services/supabase';
import { HostService } from '../../services/host';
import { LucideAngularModule, Mail, Lock, Eye, EyeOff, ArrowRight } from 'lucide-angular';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LucideAngularModule],
  template: `
    <div class="login-container">
      <!-- Animated Background -->
      <div class="gradient-bg"></div>

      <!-- Glass Card -->
      <div class="glass-card" @fadeInSlideUp>
        <!-- Logo Section -->
        <div class="logo-section">
          <div class="logo-icon">
            <span>S</span>
          </div>
          <h1 class="logo-title">Domain Scout</h1>
          <p class="logo-subtitle">Sign in to access your domain analysis dashboard</p>
        </div>

        <!-- Error Message -->
        @if (errorMessage()) {
          <div class="error-message">
            {{ errorMessage() }}
          </div>
        }

        <!-- Success Message -->
        @if (successMessage()) {
          <div class="success-message">
            {{ successMessage() }}
          </div>
        }

        <!-- Google Sign In Button -->
        <button
          class="google-btn"
          (click)="loginWithGoogle()"
          [disabled]="loading()">
          @if (loading() && authMode() === 'google') {
            <div class="spinner"></div>
            <span>Connecting...</span>
          } @else {
            <svg class="google-icon" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            <span>Continue with Google</span>
          }
        </button>

        <!-- Divider -->
        <div class="divider">
          <span>or</span>
        </div>

        <!-- Email/Password Form -->
        <form [formGroup]="loginForm" (ngSubmit)="onSubmit()" class="login-form">
          <!-- Email Field -->
          <div class="form-group">
            <div class="input-wrapper">
              <i-lucide [name]="Mail" class="input-icon"></i-lucide>
              <input
                type="email"
                formControlName="email"
                placeholder=" "
                class="form-input"
                [class.error]="loginForm.get('email')?.invalid && loginForm.get('email')?.touched">
              <label class="floating-label">Email Address</label>
            </div>
            @if (loginForm.get('email')?.invalid && (loginForm.get('email')?.touched || loginForm.get('email')?.dirty)) {
              <span class="error-text">{{ getEmailErrorMessage() }}</span>
            }
          </div>

          <!-- Password Field -->
          <div class="form-group">
            <div class="input-wrapper">
              <i-lucide [name]="Lock" class="input-icon"></i-lucide>
              <input
                [type]="showPassword() ? 'text' : 'password'"
                formControlName="password"
                placeholder=" "
                class="form-input"
                [class.error]="loginForm.get('password')?.invalid && loginForm.get('password')?.touched">
              <label class="floating-label">Password</label>
              <button
                type="button"
                class="toggle-password"
                (click)="togglePassword()">
                <i-lucide [name]="showPassword() ? EyeOff : Eye" class="toggle-icon"></i-lucide>
              </button>
            </div>
            @if (loginForm.get('password')?.invalid && (loginForm.get('password')?.touched || loginForm.get('password')?.dirty)) {
              <span class="error-text">{{ getPasswordErrorMessage() }}</span>
            }
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            class="submit-btn"
            [disabled]="loading()"
            [class.loading]="loading() && authMode() === 'email'">
            @if (loading() && authMode() === 'email') {
              <div class="spinner"></div>
              <span>Signing in...</span>
            } @else {
              <span>{{ isSignUpMode() ? 'Create Account' : 'Sign In' }}</span>
              <i-lucide [name]="ArrowRight" class="btn-icon"></i-lucide>
            }
          </button>
        </form>

        <!-- Toggle Sign Up/Sign In -->
        <div class="toggle-section">
          <p>
            {{ isSignUpMode() ? 'Already have an account?' : "Don't have an account?" }}
            <button class="toggle-btn" (click)="toggleMode()">
              {{ isSignUpMode() ? 'Sign In' : 'Sign Up' }}
            </button>
          </p>
        </div>

        <!-- Terms -->
        <p class="terms-text">
          By signing in, you agree to our <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>
        </p>
      </div>
    </div>
  `,
  styles: [`
    /* Container & Background */
    .login-container {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      position: relative;
      overflow: hidden;
    }

    .gradient-bg {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 50%, #dee2e6 100%);
      z-index: -1;
    }

    /* Glass Card */
    .glass-card {
      width: 100%;
      max-width: 420px;
      padding: 2.5rem;
      background: rgba(255, 255, 255, 0.7);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.8);
      border-radius: 24px;
      box-shadow:
        0 8px 32px rgba(0, 0, 0, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
      animation: fadeInSlideUp 0.6s ease-out;
    }

    @keyframes fadeInSlideUp {
      from {
        opacity: 0;
        transform: translateY(30px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    /* Logo Section */
    .logo-section {
      text-align: center;
      margin-bottom: 2rem;
    }

    .logo-icon {
      width: 64px;
      height: 64px;
      margin: 0 auto 1rem;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      border-radius: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }

    .logo-icon span {
      font-size: 1.75rem;
      font-weight: 800;
      color: white;
    }

    .logo-title {
      font-size: 1.75rem;
      font-weight: 700;
      color: #1f2937;
      margin-bottom: 0.5rem;
      letter-spacing: -0.02em;
    }

    .logo-subtitle {
      font-size: 0.875rem;
      color: #6b7280;
      line-height: 1.5;
    }

    /* Messages */
    .error-message {
      padding: 0.875rem 1rem;
      margin-bottom: 1rem;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.2);
      border-radius: 12px;
      color: #dc2626;
      font-size: 0.875rem;
      text-align: center;
    }

    .success-message {
      padding: 0.875rem 1rem;
      margin-bottom: 1rem;
      background: rgba(34, 197, 94, 0.1);
      border: 1px solid rgba(34, 197, 94, 0.2);
      border-radius: 12px;
      color: #16a34a;
      font-size: 0.875rem;
      text-align: center;
    }

    /* Google Button */
    .google-btn {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.75rem;
      padding: 0.875rem 1.5rem;
      background: white;
      border: none;
      border-radius: 12px;
      color: #1f2937;
      font-weight: 600;
      font-size: 0.9375rem;
      cursor: pointer;
      transition: all 0.3s ease;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .google-btn:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .google-btn:disabled {
      opacity: 0.7;
      cursor: not-allowed;
    }

    .google-icon {
      width: 20px;
      height: 20px;
    }

    /* Divider */
    .divider {
      display: flex;
      align-items: center;
      margin: 1.5rem 0;
      color: #9ca3af;
      font-size: 0.875rem;
    }

    .divider::before,
    .divider::after {
      content: '';
      flex: 1;
      height: 1px;
      background: rgba(0, 0, 0, 0.1);
    }

    .divider span {
      padding: 0 1rem;
    }

    /* Form */
    .login-form {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.375rem;
    }

    .input-wrapper {
      position: relative;
      display: flex;
      align-items: center;
    }

    .input-icon {
      position: absolute;
      left: 1rem;
      width: 20px;
      height: 20px;
      color: #9ca3af;
      pointer-events: none;
      z-index: 1;
    }

    .form-input {
      width: 100%;
      padding: 1rem 1rem 1rem 3rem;
      background: rgba(255, 255, 255, 0.8);
      border: 1px solid rgba(0, 0, 0, 0.1);
      border-radius: 12px;
      color: #1f2937;
      font-size: 0.9375rem;
      transition: all 0.3s ease;
    }

    .form-input:focus {
      outline: none;
      border-color: #6366f1;
      background: rgba(255, 255, 255, 1);
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
    }

    .form-input.error {
      border-color: rgba(239, 68, 68, 0.6);
    }

    .form-input::placeholder {
      color: transparent;
    }

    /* Floating Label */
    .floating-label {
      position: absolute;
      left: 3rem;
      top: 50%;
      transform: translateY(-50%);
      color: #9ca3af;
      font-size: 0.9375rem;
      pointer-events: none;
      transition: all 0.3s ease;
    }

    .form-input:focus ~ .floating-label,
    .form-input:not(:placeholder-shown) ~ .floating-label {
      top: 0;
      left: 0.75rem;
      transform: translateY(-50%) scale(0.85);
      background: rgba(255, 255, 255, 0.9);
      padding: 0 0.5rem;
      color: #4b5563;
    }

    .form-input:focus ~ .floating-label {
      color: #6366f1;
    }

    /* Toggle Password */
    .toggle-password {
      position: absolute;
      right: 1rem;
      background: none;
      border: none;
      cursor: pointer;
      padding: 0.25rem;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .toggle-icon {
      width: 20px;
      height: 20px;
      color: #9ca3af;
      transition: color 0.3s ease;
    }

    .toggle-password:hover .toggle-icon {
      color: #6b7280;
    }

    .error-text {
      font-size: 0.75rem;
      color: #dc2626;
      margin-left: 0.5rem;
    }

    /* Submit Button */
    .submit-btn {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 1rem 1.5rem;
      margin-top: 0.5rem;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      border: none;
      border-radius: 12px;
      color: white;
      font-weight: 600;
      font-size: 0.9375rem;
      cursor: pointer;
      transition: all 0.3s ease;
      box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }

    .submit-btn:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
    }

    .submit-btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
    }

    .btn-icon {
      width: 18px;
      height: 18px;
      transition: transform 0.3s ease;
    }

    .submit-btn:hover:not(:disabled) .btn-icon {
      transform: translateX(4px);
    }

    /* Spinner */
    .spinner {
      width: 18px;
      height: 18px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* Toggle Section */
    .toggle-section {
      text-align: center;
      margin-top: 1.5rem;
      padding-top: 1.5rem;
      border-top: 1px solid rgba(0, 0, 0, 0.1);
    }

    .toggle-section p {
      color: #6b7280;
      font-size: 0.875rem;
    }

    .toggle-btn {
      background: none;
      border: none;
      color: #6366f1;
      font-weight: 600;
      cursor: pointer;
      margin-left: 0.25rem;
      transition: color 0.3s ease;
    }

    .toggle-btn:hover {
      color: #4f46e5;
      text-decoration: underline;
    }

    /* Terms */
    .terms-text {
      text-align: center;
      margin-top: 1.5rem;
      font-size: 0.75rem;
      color: #9ca3af;
      line-height: 1.5;
    }

    .terms-text a {
      color: #6b7280;
      text-decoration: none;
      transition: color 0.3s ease;
    }

    .terms-text a:hover {
      color: #6366f1;
    }

    /* Responsive */
    @media (max-width: 480px) {
      .glass-card {
        padding: 2rem 1.5rem;
        margin: 0.5rem;
      }

      .logo-title {
        font-size: 1.5rem;
      }

      .logo-icon {
        width: 56px;
        height: 56px;
      }

      .logo-icon span {
        font-size: 1.5rem;
      }
    }
  `]
})
export class LoginComponent {
  private supabase = inject(SupabaseService);
  private router = inject(Router);
  private fb = inject(FormBuilder);
  private hostService = inject(HostService);

  // Icons
  readonly Mail = Mail;
  readonly Lock = Lock;
  readonly Eye = Eye;
  readonly EyeOff = EyeOff;
  readonly ArrowRight = ArrowRight;

  // State signals
  loading = signal(false);
  errorMessage = signal('');
  successMessage = signal('');
  showPassword = signal(false);
  isSignUpMode = signal(false);
  authMode = signal<'google' | 'email'>('email');

  // Form
  loginForm: FormGroup = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]]
  });

  constructor() {
    if (this.hostService.isBuildomainHost()) {
      this.router.navigateByUrl('/');
    }
  }

  togglePassword() {
    this.showPassword.update(v => !v);
  }

  toggleMode() {
    this.isSignUpMode.update(v => !v);
    this.errorMessage.set('');
    this.successMessage.set('');
  }

  getEmailErrorMessage() {
    const control = this.loginForm.get('email');
    if (control?.hasError('required')) return 'Email is required';
    if (control?.hasError('email')) return 'Please enter a valid email address';
    return 'Invalid email';
  }

  getPasswordErrorMessage() {
    const control = this.loginForm.get('password');
    if (control?.hasError('required')) return 'Password is required';
    if (control?.hasError('minlength')) {
      const requiredLength = control.errors?.['minlength']?.requiredLength;
      return `Minimum ${requiredLength} characters required`;
    }
    return 'Invalid password';
  }

  async loginWithGoogle() {
    this.authMode.set('google');
    this.errorMessage.set('');
    this.loading.set(true);

    try {
      console.log('Initiating Google login...');
      const { error } = await this.supabase.signInWithGoogle();
      if (error) {
        this.errorMessage.set(error.message);
      }
    } catch (err: any) {
      this.errorMessage.set(err.message || 'Failed to sign in with Google');
    } finally {
      this.loading.set(false);
    }
  }

  async onSubmit() {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.authMode.set('email');
    this.errorMessage.set('');
    this.successMessage.set('');
    this.loading.set(true);

    const { email, password } = this.loginForm.value;

    if (this.isSignUpMode()) {
      await this.handleSignUp(email, password);
    } else {
      await this.handleSignIn(email, password);
    }
  }

  private async handleSignIn(email: string, password: string) {
    try {
      const { error } = await this.supabase.signInWithEmail(email, password);
      if (error) {
        this.errorMessage.set(error.message);
      } else {
        this.router.navigateByUrl(this.hostService.appHomePath());
      }
    } catch (err: any) {
      this.errorMessage.set(err.message || 'Failed to sign in');
    } finally {
      this.loading.set(false);
    }
  }

  private async handleSignUp(email: string, password: string) {
    try {
      const { error, data } = await this.supabase.signUpWithEmail(email, password);
      if (error) {
        this.errorMessage.set(error.message);
      } else if (data.user?.identities?.length === 0) {
        this.errorMessage.set('An account with this email already exists. Please sign in instead.');
      } else {
        this.successMessage.set('Account created! Please check your email to confirm.');
        this.loginForm.reset();
      }
    } catch (err: any) {
      this.errorMessage.set(err.message || 'Failed to create account');
    } finally {
      this.loading.set(false);
    }
  }
}

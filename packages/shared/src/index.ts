// Shared types and utilities for Venmo monorepo

export type ApiResponse<T> = {
  success: true;
  data: T;
  meta?: {
    total: number;
    page: number;
    limit: number;
  };
} | {
  success: false;
  error: string;
  data: null;
};

export type UserId = string;
export type TransactionId = string;
export type Amount = number; // in cents

export type TransactionStatus = 'pending' | 'completed' | 'failed' | 'cancelled';
export type TransactionType = 'payment' | 'request' | 'transfer';

export interface User {
  id: UserId;
  email: string;
  username: string;
  displayName: string;
  createdAt: string;
}

export interface Transaction {
  id: TransactionId;
  senderId: UserId;
  recipientId: UserId;
  amount: Amount;
  note: string;
  status: TransactionStatus;
  type: TransactionType;
  createdAt: string;
  completedAt: string | null;
}

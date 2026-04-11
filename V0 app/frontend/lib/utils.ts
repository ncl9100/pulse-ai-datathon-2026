import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function getRiskColor(category: string): string {
  switch (category.toLowerCase()) {
    case "high risk":
    case "high":
      return "text-red-600";
    case "elevated":
      return "text-amber-600";
    case "moderate":
      return "text-blue-600";
    case "low risk":
    case "low":
    case "healthy":
      return "text-green-600";
    default:
      return "text-muted-foreground";
  }
}

export function getRiskBgColor(category: string): string {
  switch (category.toLowerCase()) {
    case "high risk":
    case "high":
      return "bg-red-100 text-red-700";
    case "elevated":
      return "bg-amber-100 text-amber-700";
    case "moderate":
      return "bg-blue-100 text-blue-700";
    case "low risk":
    case "low":
    case "healthy":
      return "bg-green-100 text-green-700";
    default:
      return "bg-muted text-muted-foreground";
  }
}

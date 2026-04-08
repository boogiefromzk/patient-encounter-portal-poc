import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"
import logo from "/assets/images/logo.png"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content =
    variant === "responsive" ? (
      <>
        <img
          src={logo}
          alt="Logo"
          className={cn(
            "max-w-full h-auto object-contain group-data-[collapsible=icon]:hidden",
            className,
          )}
        />
        <img
          src={logo}
          alt="Logo"
          className={cn(
            "size-8 object-contain hidden group-data-[collapsible=icon]:block",
            className,
          )}
        />
      </>
    ) : (
      <img
        src={logo}
        alt="Logo"
        className={cn(
          variant === "full" ? "max-w-full h-auto object-contain" : "size-8 object-contain",
          className,
        )}
      />
    )

  if (!asLink) {
    return content
  }

  return <Link to="/">{content}</Link>
}

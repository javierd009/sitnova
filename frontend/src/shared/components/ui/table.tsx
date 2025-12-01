'use client'

import { cn } from '@/shared/utils/cn'

interface TableProps extends React.HTMLAttributes<HTMLTableElement> {
  children: React.ReactNode
}

interface TableSectionProps extends React.HTMLAttributes<HTMLTableSectionElement> {
  children: React.ReactNode
}

export function Table({ className, children, ...props }: TableProps) {
  return (
    <div className="overflow-x-auto">
      <table
        className={cn('min-w-full divide-y divide-gray-200', className)}
        {...props}
      >
        {children}
      </table>
    </div>
  )
}

export function TableHeader({ className, children, ...props }: TableSectionProps) {
  return (
    <thead className={cn('bg-gray-50', className)} {...props}>
      {children}
    </thead>
  )
}

export function TableBody({ className, children, ...props }: TableSectionProps) {
  return (
    <tbody
      className={cn('divide-y divide-gray-200 bg-white', className)}
      {...props}
    >
      {children}
    </tbody>
  )
}

export function TableRow({ className, children, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn('hover:bg-gray-50 transition-colors', className)}
      {...props}
    >
      {children}
    </tr>
  )
}

export function TableHead({ className, children, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        'px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider',
        className
      )}
      {...props}
    >
      {children}
    </th>
  )
}

export function TableCell({ className, children, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn('px-4 py-3 whitespace-nowrap text-sm', className)}
      {...props}
    >
      {children}
    </td>
  )
}

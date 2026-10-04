import { type VariantProps, cva } from 'class-variance-authority'

export { default as Button } from './Button.vue'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[11px] text-[13px] font-semibold tracking-[.01em] cursor-pointer transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-out hover:-translate-y-px active:translate-y-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86a9d4] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none disabled:translate-y-0 motion-reduce:transition-none motion-reduce:hover:translate-y-0',
  {
    variants: {
      variant: {
        default: 'bg-[#315f9d] text-white shadow-[0_3px_10px_rgba(36,78,132,.14)] hover:bg-[#274e83] hover:shadow-[0_7px_16px_rgba(36,78,132,.18)]',
        destructive:
          'bg-[#ba554b] text-white shadow-[0_3px_10px_rgba(159,64,58,.12)] hover:bg-[#9e463d]',
        outline:
          'border border-[#d9e3ed] bg-white text-[#37506c] shadow-[0_1px_2px_rgba(35,62,94,.04)] hover:border-[#b7cbe0] hover:bg-[#f6f9fd] hover:text-[#264a79]',
        secondary:
          'bg-[#eaf1f8] text-[#315a88] hover:bg-[#dfeaf6]',
        ghost: 'text-[#4e6680] hover:bg-[#edf3fa] hover:text-[#284f80]',
        link: 'text-[#315f9d] underline-offset-4 hover:underline hover:translate-y-0',
      },
      size: {
        default: 'min-h-[44px] px-5 py-2.5',
        xs: 'min-h-[36px] px-3 text-xs',
        sm: 'min-h-[40px] px-4',
        lg: 'min-h-[48px] px-7 text-sm',
        icon: 'h-11 w-11 p-0',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export type ButtonVariants = VariantProps<typeof buttonVariants>

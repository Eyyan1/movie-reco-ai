import { Skeleton } from "@/components/ui/skeleton";

export function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-8">
      {[0, 1].map((section) => (
        <div key={section} className="flex flex-col gap-4">
          <Skeleton className="h-8 w-52 rounded-full" />
          <Skeleton className="h-5 w-96 max-w-full rounded-full" />
          <div className="flex gap-5 overflow-hidden">
            {[0, 1, 2].map((card) => (
              <Skeleton key={card} className="h-80 min-w-[300px] rounded-[1.75rem]" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

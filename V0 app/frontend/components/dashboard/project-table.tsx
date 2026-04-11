"use client";

import { useState, useMemo } from "react";
import { ArrowUpDown, Search, Filter } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn, formatCurrency, formatPercent, getRiskBgColor } from "@/lib/utils";

export interface ProjectRow {
  project_id: string;
  risk_score_0_100: number;
  risk_category: string;
  project_cpi: number;
  early_rfi_count: number;
  early_ot_ratio_pct: number;
  total_contract_value?: number;
  variance_at_completion?: number;
}

interface ProjectTableProps {
  data: ProjectRow[];
  onRowClick: (project: ProjectRow) => void;
}

type SortField = keyof ProjectRow;
type SortDirection = "asc" | "desc";

export function ProjectTable({ data, onRowClick }: ProjectTableProps) {
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState<SortField>("risk_score_0_100");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [filterCategory, setFilterCategory] = useState<string | null>(null);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const filteredData = useMemo(() => {
    let result = [...data];

    // Apply search filter
    if (search) {
      const searchLower = search.toLowerCase();
      result = result.filter((row) => row.project_id.toLowerCase().includes(searchLower));
    }

    // Apply category filter
    if (filterCategory) {
      result = result.filter((row) => row.risk_category === filterCategory);
    }

    // Apply sorting
    result.sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      if (aVal === undefined || aVal === null) return 1;
      if (bVal === undefined || bVal === null) return -1;
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDirection === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDirection === "asc" ? Number(aVal) - Number(bVal) : Number(bVal) - Number(aVal);
    });

    return result;
  }, [data, search, sortField, sortDirection, filterCategory]);

  const categories = useMemo(() => {
    return [...new Set(data.map((d) => d.risk_category))];
  }, [data]);

  const SortableHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <Button
      variant="ghost"
      size="sm"
      className="-ml-3 h-8 data-[state=open]:bg-accent"
      onClick={() => handleSort(field)}
    >
      {children}
      <ArrowUpDown
        className={cn("ml-1 h-3 w-3", sortField === field ? "opacity-100" : "opacity-40")}
      />
    </Button>
  );

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <div className="flex gap-1">
            <Button
              variant={filterCategory === null ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setFilterCategory(null)}
            >
              All
            </Button>
            {categories.map((cat) => (
              <Button
                key={cat}
                variant={filterCategory === cat ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setFilterCategory(cat)}
              >
                {cat}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>
                <SortableHeader field="project_id">Project</SortableHeader>
              </TableHead>
              <TableHead>
                <SortableHeader field="risk_score_0_100">Risk Score</SortableHeader>
              </TableHead>
              <TableHead>Category</TableHead>
              <TableHead>
                <SortableHeader field="project_cpi">CPI</SortableHeader>
              </TableHead>
              <TableHead>
                <SortableHeader field="early_rfi_count">Early RFIs</SortableHeader>
              </TableHead>
              <TableHead>
                <SortableHeader field="early_ot_ratio_pct">OT Ratio</SortableHeader>
              </TableHead>
              {data[0]?.total_contract_value !== undefined && (
                <TableHead>
                  <SortableHeader field="total_contract_value">Contract Value</SortableHeader>
                </TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                  No projects found
                </TableCell>
              </TableRow>
            ) : (
              filteredData.map((project) => (
                <TableRow
                  key={project.project_id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => onRowClick(project)}
                >
                  <TableCell className="font-medium">{project.project_id}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-12 tabular-nums">{project.risk_score_0_100.toFixed(0)}</div>
                      <div className="h-2 w-16 rounded-full bg-muted overflow-hidden">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all",
                            project.risk_score_0_100 >= 75 && "bg-red-500",
                            project.risk_score_0_100 >= 55 && project.risk_score_0_100 < 75 && "bg-amber-500",
                            project.risk_score_0_100 >= 30 && project.risk_score_0_100 < 55 && "bg-blue-500",
                            project.risk_score_0_100 < 30 && "bg-green-500"
                          )}
                          style={{ width: `${project.risk_score_0_100}%` }}
                        />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge className={getRiskBgColor(project.risk_category)} variant="secondary">
                      {project.risk_category}
                    </Badge>
                  </TableCell>
                  <TableCell className="tabular-nums">{project.project_cpi.toFixed(2)}</TableCell>
                  <TableCell className="tabular-nums">{project.early_rfi_count}</TableCell>
                  <TableCell className="tabular-nums">{formatPercent(project.early_ot_ratio_pct)}</TableCell>
                  {project.total_contract_value !== undefined && (
                    <TableCell className="tabular-nums">{formatCurrency(project.total_contract_value)}</TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <p className="text-sm text-muted-foreground">
        Showing {filteredData.length} of {data.length} projects
      </p>
    </div>
  );
}

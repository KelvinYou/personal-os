import type { Metadata } from "next";
import { TaskTeamRoom } from "@/components/office/task-team-room";
import "../office.css";
export const metadata: Metadata = { title: "Task team · Personal OS", description: "The actual runtime participants and results for the current office task." };
export default function TaskTeamPage() { return <TaskTeamRoom />; }

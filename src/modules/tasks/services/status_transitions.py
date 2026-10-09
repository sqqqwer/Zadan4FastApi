from ..resources.enums import TaskStatusEnum

ALLOWED_STATUS_TRANSITIONS: dict[TaskStatusEnum, tuple] = {
    TaskStatusEnum.CREATED: (TaskStatusEnum.ACTIVE, TaskStatusEnum.CANCELED),
    TaskStatusEnum.ACTIVE: (TaskStatusEnum.CANCELED, TaskStatusEnum.IN_PROGRESS),
    TaskStatusEnum.CANCELED: (),
    TaskStatusEnum.IN_PROGRESS: (TaskStatusEnum.NEED_REVIEW,),
    TaskStatusEnum.NEED_REVIEW: (TaskStatusEnum.IN_PROGRESS, TaskStatusEnum.COMPLETED),
    TaskStatusEnum.COMPLETED: (),
}

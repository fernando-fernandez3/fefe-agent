from autonomy.store import AutonomyStore


def test_create_and_list_learning(tmp_path):
    store = AutonomyStore(tmp_path / 'autonomy.db')
    store.create_execution(
        execution_id='exec_1',
        domain='code_projects',
        executor_type='repo_executor',
    )

    learning = store.create_learning(
        learning_id='learning_1',
        domain='code_projects',
        execution_id='exec_1',
        title='Read-only repo inspection succeeded',
        lesson='Verification evidence was attached.',
        confidence=0.8,
        actionability='reuse_readonly_repo_inspection',
        apply_as='workflow_note',
    )

    assert learning.execution_id == 'exec_1'
    assert learning.title == 'Read-only repo inspection succeeded'
    assert store.list_learnings(domain='code_projects')[0].id == 'learning_1'
    store.close()

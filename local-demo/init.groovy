import jenkins.model.Jenkins
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.SecretBytes
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.domains.Domain
import org.jenkinsci.plugins.plaincredentials.impl.FileCredentialsImpl
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import hudson.plugins.git.GitSCM
import hudson.plugins.git.UserRemoteConfig
import hudson.plugins.git.BranchSpec

def j = Jenkins.get()
def store = SystemCredentialsProvider.getInstance().getStore()
def replacement = new FileCredentialsImpl(CredentialsScope.GLOBAL, 'kubeconfig-development', 'LOCAL ONLY: namespace development SA, expires', 'development.kubeconfig', SecretBytes.fromBytes(new File('/run/local/development.kubeconfig').bytes))
def previous = SystemCredentialsProvider.getInstance().getCredentials().find { it.id == 'kubeconfig-development' }
if (previous) { store.updateCredentials(Domain.global(), previous, replacement) }
else { store.addCredentials(Domain.global(), replacement) }
if (!j.getItem('cuscatlan-local')) {
  def job = j.createProject(WorkflowJob, 'cuscatlan-local')
  def scm = new GitSCM([new UserRemoteConfig(System.getenv('LOCAL_SCM_URL'), null, null, null)], [new BranchSpec('*/main')], false, [], null, null, [])
  job.definition = new CpsScmFlowDefinition(scm, 'local-demo/Jenkinsfile')
  job.save()
}
j.save()
println('LOCAL demo job and restricted development credential configured; values omitted.')

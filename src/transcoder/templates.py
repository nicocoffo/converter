from string import Template

StartReport = Template(
"""Encoding Started:
  Source: $source
  Target: $target
  Encoding: $encoding

Encoding Report:
$encoding_report
""")

SuccessReport = Template(
"""Encoding Completed:
  Source: $source
  Target: $target
  Encoding: $encoding

Encoding Report:
$encoding_report

Job Report:
$job

Service Status:
$service""")

FailureReport = Template(
"""Encoding Failure:
  Source: $source
  Target: $target
  Encoding: $encoding

Job Report:
$job""")

# Kindle Sync Operational Runbooks

This document provides operational procedures for managing the Kindle Sync application in production.

## Table of Contents

1. [Deployment Procedures](#deployment-procedures)
2. [Monitoring and Alerting](#monitoring-and-alerting)
3. [Troubleshooting Guide](#troubleshooting-guide)
4. [Maintenance Procedures](#maintenance-procedures)
5. [Emergency Procedures](#emergency-procedures)
6. [Performance Tuning](#performance-tuning)

## Deployment Procedures

### Standard Deployment

1. **Pre-deployment Checklist**
   - [ ] All tests passing in CI/CD pipeline
   - [ ] Security scans clean
   - [ ] Configuration validated
   - [ ] Backup of current deployment created
   - [ ] Maintenance window scheduled (if required)

2. **Deployment Steps**
   ```bash
   # Deploy using the deployment script
   ./scripts/deploy.sh deploy

   # Verify deployment
   ./scripts/deploy.sh status

   # Check health endpoint
   curl http://localhost:8080/health
   ```

3. **Post-deployment Verification**
   - [ ] Health check endpoint responding
   - [ ] Metrics endpoint accessible
   - [ ] Application logs showing normal operation
   - [ ] File processing working correctly
   - [ ] Email functionality operational

### Rollback Procedure

If deployment fails or issues are detected:

```bash
# Rollback to previous version
./scripts/deploy.sh rollback

# Verify rollback
./scripts/deploy.sh status
curl http://localhost:8080/health
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **System Health**
   - Service uptime (`up{job="kindle-sync"}`)
   - Health check status
   - Memory usage
   - CPU usage

2. **Application Metrics**
   - Files processed per minute
   - Processing time (95th percentile)
   - Error rate
   - Queue size

3. **Business Metrics**
   - Emails sent successfully
   - PDF conversions completed
   - User satisfaction (if available)

### Alert Response Procedures

#### Critical Alerts

**KindleSyncDown**
- **Impact**: Service completely unavailable
- **Response Time**: 5 minutes
- **Actions**:
  1. Check container status: `docker ps -a`
  2. Check container logs: `docker logs kindle-sync-app`
  3. Restart container: `./scripts/deploy.sh restart`
  4. If restart fails, rollback: `./scripts/deploy.sh rollback`
  5. Escalate if issue persists

**EmailServiceDown**
- **Impact**: Files processed but not sent to Kindle
- **Response Time**: 15 minutes
- **Actions**:
  1. Check SMTP configuration
  2. Test email connectivity
  3. Check email service logs
  4. Verify network connectivity
  5. Contact email service provider if needed

#### Warning Alerts

**HighErrorRate**
- **Impact**: Some operations failing
- **Response Time**: 30 minutes
- **Actions**:
  1. Check error logs for patterns
  2. Identify root cause
  3. Apply fix or workaround
  4. Monitor for improvement

**ProcessingTimeHigh**
- **Impact**: Slow file processing
- **Response Time**: 1 hour
- **Actions**:
  1. Check system resources
  2. Review processing queue
  3. Consider scaling up
  4. Optimize processing logic if needed

## Troubleshooting Guide

### Common Issues

#### 1. Service Won't Start

**Symptoms**: Container fails to start or exits immediately

**Diagnosis**:
```bash
# Check container status
docker ps -a

# Check container logs
docker logs kindle-sync-app

# Check configuration
docker exec kindle-sync-app cat /app/config.yaml
```

**Common Causes**:
- Invalid configuration file
- Missing environment variables
- Port conflicts
- Insufficient resources

**Solutions**:
- Validate configuration file
- Check port availability
- Increase system resources
- Review logs for specific errors

#### 2. Files Not Processing

**Symptoms**: Files added to vault but not converted/sent

**Diagnosis**:
```bash
# Check file watcher status
curl http://localhost:8080/status

# Check processing queue
curl http://localhost:8080/metrics | grep queue

# Check application logs
docker logs kindle-sync-app | grep -i "file"
```

**Common Causes**:
- File watcher not running
- Invalid file formats
- Processing queue full
- Database connection issues

**Solutions**:
- Restart file watcher
- Check file format support
- Clear processing queue
- Verify database connectivity

#### 3. Email Sending Failures

**Symptoms**: Files processed but emails not sent

**Diagnosis**:
```bash
# Check email metrics
curl http://localhost:8080/metrics | grep email

# Check SMTP configuration
docker exec kindle-sync-app env | grep SMTP

# Test email connectivity
docker exec kindle-sync-app python -c "
import smtplib
smtp = smtplib.SMTP('smtp.gmail.com', 587)
smtp.starttls()
print('SMTP connection successful')
"
```

**Common Causes**:
- Invalid SMTP credentials
- Network connectivity issues
- Email service provider blocking
- Rate limiting

**Solutions**:
- Verify SMTP credentials
- Check network connectivity
- Contact email provider
- Implement rate limiting

#### 4. High Memory Usage

**Symptoms**: System running out of memory

**Diagnosis**:
```bash
# Check memory usage
docker stats kindle-sync-app

# Check memory metrics
curl http://localhost:8080/metrics | grep memory

# Check for memory leaks
docker exec kindle-sync-app ps aux --sort=-%mem
```

**Common Causes**:
- Memory leaks in application
- Large file processing
- Insufficient memory limits
- Too many concurrent operations

**Solutions**:
- Restart application
- Increase memory limits
- Optimize file processing
- Reduce concurrent operations

### Log Analysis

#### Key Log Locations

```bash
# Container logs
docker logs kindle-sync-app

# Application logs
tail -f logs/kindle_sync.log

# System logs
journalctl -u docker -f
```

#### Log Patterns to Watch

1. **Error Patterns**
   - `ERROR` - Application errors
   - `CRITICAL` - Critical system errors
   - `Exception` - Python exceptions
   - `Failed` - Operation failures

2. **Performance Patterns**
   - High processing times
   - Memory usage spikes
   - Queue buildup
   - Connection timeouts

3. **Security Patterns**
   - Authentication failures
   - Unauthorized access attempts
   - Suspicious file operations
   - Network anomalies

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily
- [ ] Check service health
- [ ] Review error logs
- [ ] Monitor resource usage
- [ ] Verify backup completion

#### Weekly
- [ ] Review performance metrics
- [ ] Clean up old logs
- [ ] Update security patches
- [ ] Test backup restoration

#### Monthly
- [ ] Review and rotate logs
- [ ] Update dependencies
- [ ] Performance optimization review
- [ ] Security audit

### Log Rotation

```bash
# Configure logrotate
sudo tee /etc/logrotate.d/kindle-sync << EOF
/home/kindle-sync/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 kindle-sync kindle-sync
    postrotate
        docker restart kindle-sync-app
    endscript
}
EOF
```

### Database Maintenance

```bash
# Backup database
docker exec kindle-sync-app sqlite3 /app/data/kindle_sync.db ".backup /app/data/backup_$(date +%Y%m%d).db"

# Clean old records
docker exec kindle-sync-app python -c "
from src.database import DatabaseManager
db = DatabaseManager('/app/data/kindle_sync.db')
db.cleanup_old_records(30)  # Keep 30 days
"
```

## Emergency Procedures

### Service Outage

1. **Immediate Response** (0-5 minutes)
   - Check service status
   - Restart container
   - Check system resources

2. **Short-term Response** (5-15 minutes)
   - Rollback to previous version
   - Check logs for errors
   - Notify stakeholders

3. **Long-term Response** (15+ minutes)
   - Root cause analysis
   - Implement permanent fix
   - Update monitoring/alerting

### Data Loss Prevention

1. **Immediate Actions**
   - Stop all processing
   - Backup current state
   - Assess data loss scope

2. **Recovery Actions**
   - Restore from backup
   - Replay missed operations
   - Verify data integrity

3. **Prevention Actions**
   - Improve backup frequency
   - Add data validation
   - Implement redundancy

### Security Incident

1. **Immediate Response**
   - Isolate affected systems
   - Preserve evidence
   - Notify security team

2. **Investigation**
   - Analyze logs
   - Identify attack vector
   - Assess impact

3. **Recovery**
   - Patch vulnerabilities
   - Reset credentials
   - Restore from clean backup

## Performance Tuning

### System Optimization

#### Memory Optimization
```bash
# Increase container memory limit
docker update --memory=2g kindle-sync-app

# Optimize Python memory usage
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
```

#### CPU Optimization
```bash
# Set CPU limits
docker update --cpus=2 kindle-sync-app

# Optimize processing workers
# Edit config.yaml:
# advanced:
#   async_workers: 4
#   max_workers: 8
```

#### Storage Optimization
```bash
# Use faster storage
docker run --mount type=tmpfs,destination=/tmp kindle-sync-app

# Optimize database
docker exec kindle-sync-app sqlite3 /app/data/kindle_sync.db "VACUUM;"
```

### Application Tuning

#### Processing Optimization
- Adjust worker thread count
- Optimize file processing algorithms
- Implement caching for repeated operations
- Use connection pooling

#### Monitoring Optimization
- Reduce metrics collection frequency
- Use sampling for high-volume metrics
- Implement metric aggregation
- Clean up old metrics data

### Scaling Considerations

#### Horizontal Scaling
- Use load balancer for multiple instances
- Implement shared database
- Use message queue for processing
- Implement session affinity

#### Vertical Scaling
- Increase container resources
- Optimize application code
- Use faster hardware
- Implement caching layers

## Contact Information

### Escalation Contacts

- **Level 1**: On-call engineer
- **Level 2**: Senior engineer
- **Level 3**: Engineering manager
- **Level 4**: CTO

### External Contacts

- **Email Provider**: SMTP support
- **Cloud Provider**: Infrastructure support
- **Security Team**: Security incidents
- **Legal Team**: Compliance issues

### Communication Channels

- **Slack**: #kindle-sync-alerts
- **Email**: kindle-sync-team@company.com
- **Phone**: On-call rotation
- **PagerDuty**: Critical alerts

import React, { useState, useEffect } from "react";
import {
  ChakraProvider,
  Box,
  Text,
  VStack,
  Grid,
  theme,
  FormControl,
  FormLabel,
  FormHelperText,
  Input,
  Center,
  Button,
  Link,
  Textarea,
  Flex,
  Heading,
  Spacer,
  Badge,
} from "@chakra-ui/react";

import {
  DownloadIcon,
  ExternalLinkIcon
} from "@chakra-ui/icons"

import {
  BrowserRouter as Router,
  Switch,
  Route,
  useParams,
  useHistory,
} from "react-router-dom";
import { ColorModeSwitcher } from "./ColorModeSwitcher";


function Submit() {
  const [image, setImage] = useState("golang:latest");
  const [repo, setRepo] = useState("https://github.com/lbn/ksci");
  const [steps, setSteps] = useState("cd ksci-finaliser\nfor i in $(seq 1 10); do echo $i && sleep 1; done\ngo build -o /output/ksci-finaliser\necho done!");
  const [isLoading, setIsLoading] = useState(false);
  const history = useHistory();
  const handleSubmit = event => {
    event.preventDefault();
    setIsLoading(true);
    fetch("/api/job/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        "image": image,
        "repo": repo,
        "steps": steps.split("\n"),
      })
    }).then(res => res.json()).then((result) => {
      history.push(`/job/${result.job.id}`);
    }, (error) => {
      alert("error", error);
    });
  };
  return <Box>
    <Heading size="md" p={6} textAlign="center">Submit a job to be executed</Heading>
    <form onSubmit={handleSubmit}>
      <VStack spacing={4}>
        <FormControl id="image" isRequired>
          <FormLabel>Docker image</FormLabel>
          <Input type="text" value={image} onChange={event => setImage(event.currentTarget.value)} placeholder="e.g. golang:latest" />
        </FormControl>
        <FormControl id="repo" isRequired>
          <FormLabel>Link to repository</FormLabel>
          <Input type="text" value={repo} onChange={event => setRepo(event.currentTarget.value)} />
          <FormHelperText>This repository will be cloned in the container</FormHelperText>
        </FormControl>
        <FormControl id="steps" isRequired>
          <FormLabel>Pipeline steps</FormLabel>
          <Textarea fontFamily="mono" value={steps} onChange={event => setSteps(event.currentTarget.value)} placeholder="e.g. echo hello && go build" />
        </FormControl>
        <Button colorScheme="blue" type="submit" isLoading={isLoading}>Submit</Button>
      </VStack>
    </form>
  </Box>
}


function Job() {
  const { jobId } = useParams();
  const [status, setStatus] = useState({ status: "unknown" });
  const [job, setJob] = useState({
    repo: "",
    objectIdLogs: null
  });
  const [objectIdLog, setObjectIdLog] = useState(null);
  const [logs, setLogs] = useState([]);
  const colours = {
    pending: "gray",
    running: "yellow",
    succeeded: "green",
    failed: "red"
  };
  const terminatedStatuses = ["succeeded", "failed"];

  let lastLogID = null;

  async function getJob() {
    return (await fetch(`/api/job/${jobId}`, {
      headers: {
        "accepts": "application/json"
      }
    })).json();
  }
  async function getStatus() {
    const res = await fetch(`/api/job/${jobId}/status`, {
      headers: {
        "accepts": "application/json"
      }
    });
    return res.json()
  }
  async function getLogs(objectId) {
    let params = {};
    if (lastLogID != null) {
      params["after-id"] = lastLogID;
    }
    const res = await fetch(`/api/log/${objectId}?` + new URLSearchParams(params), {
      headers: {
        "accepts": "application/json"
      }
    });
    const logLines = await res.text();
    if (logLines.length > 0) {
      lastLogID = res.headers.get("Last-Log-Id");
    }
    return logLines.split("\n");
  }
  useEffect(() => {
    async function init() {
      // Initial job load
      const jobRes = await getJob();
      setJob(jobRes);
      setLogs(await getLogs(jobRes.log_id));
      setObjectIdLog(jobRes.log_id);
    }
    init();
  }, []);

  useEffect(() => {
    // Status updater
    const interval = setInterval(async () => {
      const newStatus = await getStatus();
      if (newStatus.id !== status.id) {
        setStatus(newStatus);
      }
      if (terminatedStatuses.includes(status.status)) {
        clearInterval(interval);
        return
      }
    }, 1000);
    return () => {
      clearInterval(interval);
    }
  }, [status]);


  useEffect(() => {
    // Log updater for "running" only
    if (status.status !== "running") {
      return;
    }
    const interval = setInterval(async () => {
      const newLogs = await getLogs(objectIdLog);
      setLogs(oldLogs => {
        return oldLogs.concat(newLogs);
      });
      if (terminatedStatuses.includes(status.status)) {
        clearInterval(interval);
        return
      }
    }, 1000);
    return () => {
      clearInterval(interval);
    }
  }, [status, objectIdLog]);
  return <Box>
    <Heading size="md" p={6} textAlign="center">Job status</Heading>
    <VStack align="stretch" spacing={4}>
      <Flex>
        <Box p="2" >
          <Heading size="md">{jobId}</Heading>
          <Link href={job.repo} isExternal value="aa">
            {job.repo} <ExternalLinkIcon mx="2px" />
          </Link>
        </Box>
        <Spacer />
        <VStack p="2">
          <Badge ml="1" colorScheme={colours[status.status]}>
            {status.status}
          </Badge>
          <Button as="a" href={`/api/object/${job.output_object_id}?output`} target="blank" leftIcon={<DownloadIcon />} colorScheme="blue" size="sm" disabled={status.status !== "succeeded"}>Download</Button>
        </VStack>
      </Flex>
      <Box background="black" color="white" fontFamily="mono" borderRadius="lg" p={2} minHeight={10}>
        {logs.length > 0 ? logs.map((line, index) => <Text key={index}>{line}</Text>) : (<Text color="gray">...</Text>)}
      </Box>
    </VStack>
  </Box >
}

function App() {
  return (
    <Router>
      <ChakraProvider theme={theme}>
        <Center>
          <Grid minW="container.md" p={3}>
            <ColorModeSwitcher justifySelf="flex-end" />
            <Heading textAlign="center" p={6} fontSize="5xl">ksci</Heading>
            <Switch>
              <Route path="/job/:jobId"><Job /></Route>
              <Route path="/"><Submit /></Route>
            </Switch>
          </Grid>
        </Center>
      </ChakraProvider>
    </Router>
  );
}

export default App;
